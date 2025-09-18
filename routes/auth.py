from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.logging_config import SecurityEvent, get_logger, log_security_event
from core.helpers.phone_utils import validate_phone_number
from routes.dependencies import bcrypt, db, templates, u

router = APIRouter()
logger = get_logger("auth")


@router.get("/login")
async def login_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("login.html", {"request": request})
    )


@router.get("/register")
async def register_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("register.html", {"request": request})
    )


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.lower().strip()
    ip_address = request.client.host if request.client else "unknown"

    try:
        res = db(
            "SELECT id, password_hash FROM anglers WHERE email=:email",
            {"email": email},
        )
        if res and len(res) > 0 and res[0]["password_hash"]:  # Check if password_hash exists
            if bcrypt.checkpw(password.encode(), res[0]["password_hash"].encode()):
                user_id = res[0]["id"]
                request.session["user_id"] = user_id
                log_security_event(
                    SecurityEvent.AUTH_LOGIN_SUCCESS,
                    user_id=user_id,
                    user_email=email,
                    ip_address=ip_address,
                    details={"method": "password"},
                )
                logger.info(
                    "User login successful",
                    extra={"user_id": user_id, "user_email": email, "ip_address": ip_address},
                )
                return RedirectResponse("/", status_code=302)
        log_security_event(
            SecurityEvent.AUTH_LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            details={"reason": "invalid_credentials", "method": "password"},
        )
        logger.warning(
            "Login attempt failed - invalid credentials",
            extra={"user_email": email, "ip_address": ip_address},
        )
    except Exception as e:
        logger.error(
            "Login error",
            extra={"user_email": email, "ip_address": ip_address, "error": str(e)},
            exc_info=True,
        )
        log_security_event(
            SecurityEvent.AUTH_LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            details={"reason": "system_error", "error": str(e)},
        )
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid email or password"}
    )


@router.post("/register")
async def register(
    request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    email = email.lower().strip()
    name = name.strip()
    ip_address = request.client.host if request.client else "unknown"
    try:
        existing = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if existing:
            logger.warning(
                "Registration attempt with existing email",
                extra={"user_email": email, "ip_address": ip_address},
            )
            return templates.TemplateResponse(
                "login.html", {"request": request, "error": "Email already exists"}
            )

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db(
            "INSERT INTO anglers (name, email, password_hash, member, is_admin) VALUES (:name, :email, :password_hash, 1, 0)",
            {"name": name, "email": email, "password_hash": password_hash},
        )
        user = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if user:
            user_id = user[0]["id"]
            request.session["user_id"] = user_id
            log_security_event(
                SecurityEvent.AUTH_REGISTER,
                user_id=user_id,
                user_email=email,
                ip_address=ip_address,
                details={"name": name, "method": "self_register"},
            )
            logger.info(
                "User registration successful",
                extra={
                    "user_id": user_id,
                    "user_name": name,
                    "user_email": email,
                    "ip_address": ip_address,
                },
            )
            return RedirectResponse("/", status_code=302)
    except Exception as e:
        logger.error(
            "Registration error",
            extra={
                "user_name": name,
                "user_email": email,
                "ip_address": ip_address,
                "error": str(e),
            },
            exc_info=True,
        )
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Registration failed"}
        )
    return RedirectResponse("/login", status_code=302)


@router.get("/profile")
async def profile_page(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")
    user_data = db(
        "SELECT id, name, email, member, is_admin, phone, year_joined, created_at FROM anglers WHERE id = :id",
        {"id": user["id"]},
    )
    if not user_data:
        return RedirectResponse("/login")

    user_profile = {
        "id": user_data[0]["id"],
        "name": user_data[0]["name"],
        "email": user_data[0]["email"],
        "member": bool(user_data[0]["member"]),
        "is_admin": bool(user_data[0]["is_admin"]),
        "phone": user_data[0]["phone"],
        "year_joined": user_data[0]["year_joined"],
        "created_at": user_data[0]["created_at"],
    }
    current_year = datetime.now().year
    res = db(
        """
        SELECT COUNT(DISTINCT t.id)
        FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE r.angler_id = :user_id AND NOT r.disqualified
    """,
        {"user_id": user["id"]},
    )
    tournaments_count = res[0][0] if res and len(res) > 0 else 0
    res = db(
        """
        SELECT COALESCE(MAX(r.total_weight - COALESCE(r.dead_fish_penalty, 0)), 0)
        FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        WHERE r.angler_id = :user_id AND NOT r.disqualified
    """,
        {"user_id": user["id"]},
    )
    best_weight = res[0][0] if res and len(res) > 0 else 0
    res = db(
        """
        SELECT COALESCE(MAX(r.big_bass_weight), 0)
        FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        WHERE r.angler_id = :user_id AND NOT r.disqualified
    """,
        {"user_id": user["id"]},
    )
    big_bass = res[0][0] if res and len(res) > 0 else 0
    current_finishes = db(
        """
        SELECT
            SUM(CASE WHEN place = 1 THEN 1 ELSE 0 END) as first,
            SUM(CASE WHEN place = 2 THEN 1 ELSE 0 END) as second,
            SUM(CASE WHEN place = 3 THEN 1 ELSE 0 END) as third
        FROM (
            SELECT ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place
            FROM team_results tr
            JOIN tournaments t ON tr.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE (tr.angler1_id = :user_id OR tr.angler2_id = :user_id)
            AND e.year = :current_year
        )
    """,
        {"user_id": user["id"], "current_year": current_year},
    )
    current_first, current_second, current_third = (
        current_finishes[0] if current_finishes else (0, 0, 0)
    )
    all_time_finishes = db(
        """
        SELECT
            SUM(CASE WHEN place = 1 THEN 1 ELSE 0 END) as first,
            SUM(CASE WHEN place = 2 THEN 1 ELSE 0 END) as second,
            SUM(CASE WHEN place = 3 THEN 1 ELSE 0 END) as third
        FROM (
            SELECT ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place
            FROM team_results tr
            JOIN tournaments t ON tr.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE (tr.angler1_id = :user_id OR tr.angler2_id = :user_id)
            AND e.year >= 2022
        )
    """,
        {"user_id": user["id"]},
    )
    all_time_first, all_time_second, all_time_third = (
        all_time_finishes[0] if all_time_finishes else (0, 0, 0)
    )
    aoy_position = None
    try:
        aoy_standings = db(
            """
            WITH tournament_standings AS (
                SELECT
                    r.angler_id,
                    r.tournament_id,
                    r.total_weight - COALESCE(r.dead_fish_penalty, 0) as adjusted_weight,
                    r.num_fish,
                    r.disqualified,
                    r.buy_in,
                    DENSE_RANK() OVER (
                        PARTITION BY r.tournament_id
                        ORDER BY
                            CASE WHEN r.disqualified = true THEN 0 ELSE r.total_weight - COALESCE(r.dead_fish_penalty, 0) END DESC
                    ) as place_finish,
                    COUNT(*) OVER (PARTITION BY r.tournament_id) as total_participants
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE e.year = :current_year
            ),
            points_calc AS (
                SELECT
                    angler_id,
                    tournament_id,
                    adjusted_weight,
                    num_fish,
                    place_finish,
                    CASE
                        WHEN disqualified = true THEN 0
                        ELSE 101 - place_finish
                    END as points
                FROM tournament_standings
            ),
            aoy_standings AS (
                SELECT
                    a.id,
                    a.name,
                    SUM(CASE WHEN a.member = true THEN pc.points ELSE 0 END) as total_points,
                    SUM(pc.adjusted_weight) as total_weight,
                    ROW_NUMBER() OVER (ORDER BY SUM(CASE WHEN a.member = true THEN pc.points ELSE 0 END) DESC, SUM(pc.adjusted_weight) DESC) as position
                FROM anglers a
                JOIN points_calc pc ON a.id = pc.angler_id
                WHERE a.member = true
                GROUP BY a.id, a.name
            )
            SELECT position
            FROM aoy_standings
            WHERE id = :user_id
        """,
            {"current_year": current_year, "user_id": user["id"]},
        )
        if aoy_standings:
            aoy_position = (
                aoy_standings[0]["position"]
                if "position" in aoy_standings[0]
                else aoy_standings[0][0]
            )
    except Exception:
        pass

    stats = {
        "tournaments": tournaments_count,
        "best_weight": best_weight,
        "big_bass": big_bass,
        "current_first": current_first or 0,
        "current_second": current_second or 0,
        "current_third": current_third or 0,
        "all_time_first": all_time_first or 0,
        "all_time_second": all_time_second or 0,
        "all_time_third": all_time_third or 0,
        "aoy_position": aoy_position,
    }
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user_profile,
            "stats": stats,
            "current_year": current_year,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/profile/update")
async def update_profile(
    request: Request,
    email: str = Form(...),
    phone: str = Form(""),
    year_joined: int = Form(None),
):
    if not (user := u(request)):
        return RedirectResponse("/login")

    try:
        email = email.lower().strip()
        is_valid, formatted_phone, error_msg = validate_phone_number(phone)
        if not is_valid:
            return RedirectResponse(f"/profile?error={error_msg}")
        phone = formatted_phone
        existing_email = db(
            "SELECT id FROM anglers WHERE email = :email AND id != :user_id",
            {"email": email, "user_id": user["id"]},
        )
        if existing_email:
            return RedirectResponse("/profile?error=Email is already in use by another user")

        db(
            """
            UPDATE anglers
            SET email = :email, phone = :phone, year_joined = :year_joined
            WHERE id = :user_id
        """,
            {
                "email": email,
                "phone": phone,
                "year_joined": year_joined,
                "user_id": user["id"],
            },
        )
        logger.info(
            "User profile updated",
            extra={
                "user_id": user["id"],
                "updated_fields": {
                    "email": email,
                    "phone": phone,
                    "year_joined": year_joined,
                },
            },
        )
        return RedirectResponse("/profile?success=Profile updated successfully", status_code=302)
    except Exception as e:
        logger.error(
            "Profile update error",
            extra={"user_id": user["id"], "error": str(e)},
            exc_info=True,
        )
        return RedirectResponse("/profile?error=Failed to update profile")


@router.post("/profile/delete")
async def delete_profile(request: Request, confirm: str = Form(...)):
    if not (user := u(request)):
        return RedirectResponse("/login")
    if confirm != "DELETE":
        return RedirectResponse("/profile?error=Confirmation text must be exactly 'DELETE'")

    try:
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        logger.warning(
            "User account self-deletion",
            extra={"user_id": user_id, "user_email": user_email},
        )
        log_security_event(
            SecurityEvent.AUTH_ACCOUNT_DELETED,
            user_id=user_id,
            user_email=user_email,
            ip_address=request.client.host if request.client else "unknown",
            details={"method": "self_delete"},
        )
        db("DELETE FROM anglers WHERE id = :user_id", {"user_id": user_id})
        request.session.clear()
        return RedirectResponse("/?success=Account deleted successfully", status_code=302)
    except Exception as e:
        logger.error(
            "Account deletion error",
            extra={"user_id": user["id"], "error": str(e)},
            exc_info=True,
        )
        return RedirectResponse("/profile?error=Failed to delete account")


@router.post("/logout")
async def logout(request: Request):
    user_id = request.session.get("user_id")
    ip_address = request.client.host if request.client else "unknown"
    if user_id:
        try:
            user_info = db("SELECT email FROM anglers WHERE id = :user_id", {"user_id": user_id})
            user_email = user_info[0]["email"] if user_info and len(user_info) > 0 else None
            log_security_event(
                SecurityEvent.AUTH_LOGOUT,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
            )
            logger.info(
                "User logout",
                extra={"user_id": user_id, "user_email": user_email, "ip_address": ip_address},
            )
        except Exception as e:
            logger.error(
                "Error logging logout event",
                extra={"user_id": user_id, "ip_address": ip_address, "error": str(e)},
            )
    request.session.clear()
    return RedirectResponse("/", status_code=302)
