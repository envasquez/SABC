# -*- coding: utf-8 -*-

import time
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse


def rate_limit(requests=10, window=60, key_func=None):
    """
    Rate limiting decorator for views

    Args:
        requests: Number of requests allowed
        window: Time window in seconds
        key_func: Function to generate cache key (default: IP address)
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(request)
            else:
                ip = get_client_ip(request)
                cache_key = f"rate_limit:{view_func.__name__}:{ip}"

            # Check rate limit
            if is_rate_limited(cache_key, requests, window):
                response = HttpResponse(
                    "Rate limit exceeded. Please try again later.",
                    content_type="text/plain",
                    status=429,
                )
                return response

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def login_required_with_rate_limit(requests=5, window=300):
    """
    Combined login required and rate limiting decorator
    """

    def decorator(view_func):
        from django.contrib.auth.decorators import login_required

        @rate_limit(requests=requests, window=window)
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_client_ip(request):
    """Get the client's IP address from request headers"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def is_rate_limited(cache_key, requests, window):
    """Check if a cache key is rate limited"""
    # Get current request count and timestamp
    data = cache.get(cache_key, {"count": 0, "reset_time": time.time()})
    current_time = time.time()

    # Reset counter if time window has passed
    if current_time > data["reset_time"] + window:
        data = {"count": 0, "reset_time": current_time}

    # Check if limit exceeded
    if data["count"] >= requests:
        return True

    # Increment counter
    data["count"] += 1
    cache.set(cache_key, data, window)

    return False


def user_rate_limit(requests=20, window=60):
    """
    Rate limiting based on user ID (for authenticated users)
    """

    def key_func(request):
        if request.user.is_authenticated:
            return f"user_rate_limit:{request.user.id}"
        else:
            ip = get_client_ip(request)
            return f"ip_rate_limit:{ip}"

    return rate_limit(requests=requests, window=window, key_func=key_func)
