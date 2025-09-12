"""Authentication decorators to reduce repetitive auth patterns."""

from functools import wraps

from fastapi import Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import u


def require_admin(func):
    """Decorator that ensures user is authenticated and is an admin."""

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not (user := u(request)) or not user.get("is_admin"):
            return RedirectResponse("/login")
        return await func(request, *args, **kwargs)

    return wrapper


def require_auth(func):
    """Decorator that ensures user is authenticated."""

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not u(request):
            return RedirectResponse("/login")
        return await func(request, *args, **kwargs)

    return wrapper
