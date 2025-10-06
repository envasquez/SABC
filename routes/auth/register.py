from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from routes.dependencies import bcrypt, db, templates, u

router = APIRouter()
logger = get_logger("auth.register")


@router.get("/register")
async def register_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("register.html", {"request": request})
    )


@router.post("/register")
async def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.lower().strip()
    first_name = first_name.strip()
    last_name = last_name.strip()
    name = f"{first_name} {last_name}".strip()
    ip_address = request.client.host if request.client else "unknown"

    # Validate password strength
    if len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be at least 8 characters"},
        )

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
            "INSERT INTO anglers (name, email, password, member, is_admin) VALUES (:name, :email, :password, FALSE, FALSE)",
            {"name": name, "email": email, "password": password_hash},
        )

        user = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if user:
            user_id = user[0][0]
            # Clear session to prevent session fixation attacks
            request.session.clear()
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
