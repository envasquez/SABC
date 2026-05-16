import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, get_session
from core.helpers.forms import normalize_email
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.password_validator import validate_password_strength
from core.helpers.passwords import bcrypt_gensalt
from core.helpers.response import set_user_session
from routes.dependencies import bcrypt, get_current_user, templates

router = APIRouter()
logger = get_logger("auth.register")
# Disable rate limiting in test environment
is_test_env = os.environ.get("ENVIRONMENT") == "test"
limiter = Limiter(key_func=get_remote_address, enabled=not is_test_env)


@router.get("/register")
async def register_page(request: Request) -> Response:
    return (
        RedirectResponse("/")
        if get_current_user(request)
        else templates.TemplateResponse(request, "register.html", {})
    )


@router.get("/auth/register")
async def register_page_auth(request: Request) -> Response:
    """Alternative route for /auth/register."""
    return (
        RedirectResponse("/")
        if get_current_user(request)
        else templates.TemplateResponse(request, "register.html", {})
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
    email = normalize_email(email)
    first_name = first_name.strip()
    last_name = last_name.strip()
    name = f"{first_name} {last_name}".strip()
    ip_address = request.client.host if request.client else "unknown"

    # Validate password strength
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
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
                    request,
                    "register.html",
                    {
                        "error": "Email already exists",
                        "first_name": first_name,
                        "last_name": last_name,
                        # Don't pre-fill email when it's the error
                    },
                )

            # Create new angler
            password_hash = bcrypt.hashpw(password.encode(), bcrypt_gensalt()).decode()
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
            user_session_version = new_angler.session_version

        # Clear session to prevent session fixation attacks and embed
        # the new angler's session_version (default 1) so subsequent
        # requests pass the version check in get_current_user.
        set_user_session(request, user_id, user_session_version)
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
        return RedirectResponse("/", status_code=303)
    except (SQLAlchemyError, ValueError) as e:
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
            request,
            "register.html",
            {
                "error": "Registration failed",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )
