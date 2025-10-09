from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.db_schema import Angler, get_session
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.password_validator import validate_password_strength
from routes.dependencies import bcrypt, templates, u

router = APIRouter()
logger = get_logger("auth.register")
limiter = Limiter(key_func=get_remote_address)


@router.get("/register")
async def register_page(request: Request) -> Response:
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("register.html", {"request": request})
    )


@router.post("/register")
@limiter.limit("3/hour")
async def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    email = email.lower().strip()
    first_name = first_name.strip()
    last_name = last_name.strip()
    name = f"{first_name} {last_name}".strip()
    ip_address = request.client.host if request.client else "unknown"

    # Validate password strength
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": error_message,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )

    try:
        with get_session() as session:
            # Check if email already exists
            existing = session.query(Angler).filter(Angler.email == email).first()
            if existing:
                logger.warning(
                    "Registration attempt with existing email",
                    extra={"user_email": email, "ip_address": ip_address},
                )
                return templates.TemplateResponse(
                    "register.html",
                    {
                        "request": request,
                        "error": "Email already exists",
                        "first_name": first_name,
                        "last_name": last_name,
                        # Don't pre-fill email when it's the error
                    },
                )

            # Create new angler
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            new_angler = Angler(
                name=name,
                email=email,
                password_hash=password_hash,
                member=False,
                is_admin=False,
            )
            session.add(new_angler)
            session.flush()  # Get the ID before commit
            user_id = new_angler.id

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
            "register.html",
            {
                "request": request,
                "error": "Registration failed",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )
    return RedirectResponse("/login", status_code=302)
