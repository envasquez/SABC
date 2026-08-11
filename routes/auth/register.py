import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.db_schema import Angler, get_session
from core.helpers.db_errors import is_duplicate_email_error
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
def register_page(request: Request) -> Response:
    return (
        RedirectResponse("/")
        if get_current_user(request)
        else templates.TemplateResponse(request, "register.html", {})
    )


def _account_exists_response(request: Request, first_name: str, last_name: str) -> Response:
    """Re-render the signup form explaining that the address is already in use.

    The email is deliberately not echoed back into the form — it is the one
    field we are declining, so pre-filling it just invites an identical resubmit
    that burns another of the three hourly attempts.
    """
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "account_exists": True,
            "first_name": first_name,
            "last_name": last_name,
        },
    )


def _registration_failed_response(
    request: Request, first_name: str, last_name: str, email: str
) -> Response:
    """Re-render the signup form after an unexpected failure, preserving input."""
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "error": "Registration failed. Please try again.",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        },
    )


@router.get("/auth/register")
def register_page_auth(request: Request) -> Response:
    """Alternative route for /auth/register."""
    return (
        RedirectResponse("/")
        if get_current_user(request)
        else templates.TemplateResponse(request, "register.html", {})
    )


@router.post("/register")
@limiter.limit("3/hour")
def register(
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

    # Hash before opening the transaction. bcrypt is deliberately slow (~300ms),
    # and doing it mid-transaction had three costs: it held a pooled connection
    # idle, it stretched the window between the duplicate-email check and the
    # INSERT wide enough for concurrent submits to race through, and it made the
    # "email already taken" path measurably faster to respond than the "email is
    # new" path — a timing oracle for probing which addresses are registered.
    # Hashing up front closes all three.
    password_hash = bcrypt.hashpw(password.encode(), bcrypt_gensalt()).decode()

    try:
        with get_session() as session:
            # Check if email already exists. This is the fast path for the
            # common case; it is NOT the safety net. The unique constraint is,
            # and the IntegrityError handler below covers the gap between this
            # SELECT and the INSERT.
            existing = session.query(Angler).filter(Angler.email == email).first()
            if existing:
                logger.warning(
                    "Registration attempt with existing email",
                    extra={"user_email": email, "ip_address": ip_address},
                )
                return _account_exists_response(request, first_name, last_name)

            # Create new angler
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
    except IntegrityError as e:
        # Two submits for the same address can both clear the SELECT above and
        # then collide on the unique index — a double-clicked submit button is
        # enough, since only the INSERT actually serialises them. That is a
        # duplicate registration, not a server fault, so it gets the same
        # friendly response as the checked path rather than a 500-shaped error.
        if is_duplicate_email_error(e):
            logger.warning(
                "Registration attempt with existing email (concurrent submit)",
                extra={"user_email": email, "ip_address": ip_address},
            )
            return _account_exists_response(request, first_name, last_name)
        # Any other integrity failure is a real defect — surface it to Sentry.
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
        return _registration_failed_response(request, first_name, last_name, email)
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
        return _registration_failed_response(request, first_name, last_name, email)
