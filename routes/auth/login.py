import os
import threading
import time
from collections import OrderedDict
from typing import List

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, get_session
from core.helpers.forms import normalize_email
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.passwords import bcrypt_gensalt
from core.helpers.response import get_client_ip, get_safe_redirect_url, set_user_session
from routes.dependencies import bcrypt, get_current_user, templates

router = APIRouter()
logger = get_logger("auth.login")
# Disable rate limiting in test environment
is_test_env = os.environ.get("ENVIRONMENT") == "test"
limiter = Limiter(key_func=get_remote_address, enabled=not is_test_env)

# --- Account lockout (defense-in-depth alongside rate limiting) ---
_MAX_FAILED_ATTEMPTS = 10
_LOCKOUT_SECONDS = 900  # 15 minutes
# Cap total number of tracked emails to bound memory growth from attackers
# submitting unique random emails.
_FAILED_ATTEMPTS_MAX = 10000
_failed_attempts: "OrderedDict[str, List[float]]" = OrderedDict()
_lockout_lock = threading.Lock()


def _purge_expired_entries() -> None:
    """Drop entries whose newest attempt is older than the lockout window.

    Caller MUST hold _lockout_lock.
    """
    cutoff = time.monotonic() - _LOCKOUT_SECONDS
    # Iterate over a snapshot of keys since we mutate during iteration.
    for email in list(_failed_attempts.keys()):
        attempts = _failed_attempts[email]
        if not attempts or attempts[-1] <= cutoff:
            del _failed_attempts[email]


def _is_account_locked(email: str) -> bool:
    """Check if an account is temporarily locked due to failed login attempts."""
    with _lockout_lock:
        attempts = _failed_attempts.get(email)
        if not attempts:
            return False
        cutoff = time.monotonic() - _LOCKOUT_SECONDS
        fresh = [t for t in attempts if t > cutoff]
        if fresh:
            _failed_attempts[email] = fresh
        else:
            _failed_attempts.pop(email, None)
        return len(fresh) >= _MAX_FAILED_ATTEMPTS


def _record_failed_attempt(email: str) -> None:
    with _lockout_lock:
        # Opportunistic purge of stale entries before bookkeeping.
        _purge_expired_entries()
        if email in _failed_attempts:
            # Move-to-end so this key becomes the most-recently-used.
            _failed_attempts.move_to_end(email)
            _failed_attempts[email].append(time.monotonic())
            return
        # New key — enforce the size cap by evicting the oldest entry first.
        if len(_failed_attempts) >= _FAILED_ATTEMPTS_MAX:
            _failed_attempts.popitem(last=False)
        _failed_attempts[email] = [time.monotonic()]


def _clear_failed_attempts(email: str) -> None:
    with _lockout_lock:
        _failed_attempts.pop(email, None)


@router.get("/login")
async def login_page(request: Request) -> Response:
    if get_current_user(request):
        return RedirectResponse("/")

    # Extract query parameters for success/error messages and next redirect
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    next_url = request.query_params.get("next", "/")

    return templates.TemplateResponse(
        request,
        "login.html",
        {
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
    email = normalize_email(email)
    ip_address = get_client_ip(request)

    # Validate next_url to prevent open redirect attacks
    safe_next_url = get_safe_redirect_url(next_url, default="/")

    # Account lockout check (per-email, complements per-IP rate limiting)
    if _is_account_locked(email):
        log_security_event(
            SecurityEvent.AUTH_LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            details={"reason": "account_locked"},
        )
        logger.warning(
            "Login rejected - account temporarily locked",
            extra={"user_email": email, "ip_address": ip_address},
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Too many failed attempts. Please try again later."},
        )

    try:
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.email == email).first()

            # Extract data while still in session context (avoid detached instance error)
            if angler and angler.password_hash:
                stored_hash = angler.password_hash.encode()
                user_id = angler.id
                user_name = angler.name
                user_session_version = angler.session_version
            else:
                # User doesn't exist - perform dummy hash to prevent timing attack
                stored_hash = bcrypt.hashpw(b"dummy_password", bcrypt_gensalt())
                user_id = None
                user_name = None
                user_session_version = 1

        # Always perform comparison (constant time regardless of user existence)
        password_valid = bcrypt.checkpw(password.encode(), stored_hash)

        # Successful login
        if password_valid and user_id:
            _clear_failed_attempts(email)
            set_user_session(request, user_id, user_session_version)
            log_security_event(
                SecurityEvent.AUTH_LOGIN_SUCCESS,
                user_id=user_id,
                user_email=email,
                ip_address=ip_address,
                details={"method": "password"},
            )
            logger.info(
                f"User login successful: {user_name}",
                extra={
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_email": email,
                    "ip_address": ip_address,
                },
            )
            return RedirectResponse(safe_next_url, status_code=303)

        # Failed login - log but don't reveal whether email exists
        _record_failed_attempt(email)
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

    return templates.TemplateResponse(request, "login.html", {"error": "Invalid email or password"})


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
