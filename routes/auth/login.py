import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, get_session
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.response import get_client_ip, set_user_session
from routes.dependencies import bcrypt, get_current_user, templates

router = APIRouter()
logger = get_logger("auth.login")
# Disable rate limiting in test environment
is_test_env = os.environ.get("ENVIRONMENT") == "test"
limiter = Limiter(key_func=get_remote_address, enabled=not is_test_env)


@router.get("/login")
async def login_page(request: Request) -> Response:
    if get_current_user(request):
        return RedirectResponse("/")

    # Extract query parameters for success/error messages and next redirect
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    next_url = request.query_params.get("next", "/")

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "success": success,
            "error": error,
            "next_url": next_url,
        },
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/"),
) -> Response:
    email = email.lower().strip()
    ip_address = get_client_ip(request)

    # Validate next_url to prevent open redirect attacks
    # Only allow relative URLs (must start with /) and reject external URLs
    safe_next_url = "/"
    if next_url and isinstance(next_url, str):
        # Remove leading/trailing whitespace
        next_url = next_url.strip()
        # Only allow relative URLs starting with /
        if next_url.startswith("/") and not next_url.startswith("//"):
            # Reject URLs with schemes (http://, https://, etc.)
            if "://" not in next_url:
                safe_next_url = next_url

    try:
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.email == email).first()

            # Extract data while still in session context (avoid detached instance error)
            if angler and angler.password_hash:
                stored_hash = angler.password_hash.encode()
                user_id = angler.id
            else:
                # User doesn't exist - perform dummy hash to prevent timing attack
                stored_hash = bcrypt.hashpw(b"dummy_password", bcrypt.gensalt())
                user_id = None

        # Always perform comparison (constant time regardless of user existence)
        password_valid = bcrypt.checkpw(password.encode(), stored_hash)

        # Successful login
        if password_valid and user_id:
            set_user_session(request, user_id)
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
            return RedirectResponse(safe_next_url, status_code=303)

        # Failed login - log but don't reveal whether email exists
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

    except SQLAlchemyError as e:
        logger.error(
            "Database error during login",
            extra={"user_email": email, "ip_address": ip_address, "error": str(e)},
            exc_info=True,
        )
        log_security_event(
            SecurityEvent.AUTH_LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            details={"reason": "database_error"},
        )

    except Exception as e:
        logger.critical(
            "Unexpected error during login",
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
async def logout(request: Request) -> RedirectResponse:
    user_id = request.session.get("user_id")
    ip_address = get_client_ip(request)

    if user_id:
        log_security_event(
            SecurityEvent.AUTH_LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
        )
        logger.info("User logout", extra={"user_id": user_id, "ip_address": ip_address})
    request.session.clear()
    return RedirectResponse("/", status_code=303)
