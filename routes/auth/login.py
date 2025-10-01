from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from routes.dependencies import bcrypt, db, templates, u

router = APIRouter()
logger = get_logger("auth.login")


@router.get("/login")
async def login_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("login.html", {"request": request})
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
        if res and len(res) > 0 and res[0][1]:
            if bcrypt.checkpw(password.encode(), res[0][1].encode()):
                user_id = res[0][0]
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


@router.post("/logout")
async def logout(request: Request):
    user_id = request.session.get("user_id")
    ip_address = request.client.host if request.client else "unknown"

    if user_id:
        log_security_event(
            SecurityEvent.AUTH_LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
        )
        logger.info("User logout", extra={"user_id": user_id, "ip_address": ip_address})
    request.session.clear()
    return RedirectResponse("/", status_code=302)
