# -*- coding: utf-8 -*-

import time

from django.conf import settings
from django.core.cache import cache, caches
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware that tracks requests per IP address
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        # Default rate limits (requests per time window)
        self.rate_limits = getattr(
            settings,
            "RATE_LIMITS",
            {
                "default": {"requests": 60, "window": 60},  # 60 requests per minute
                "login": {
                    "requests": 5,
                    "window": 300,
                },  # 5 login attempts per 5 minutes
                "register": {
                    "requests": 3,
                    "window": 600,
                },  # 3 registrations per 10 minutes
                "upload": {"requests": 10, "window": 300},  # 10 uploads per 5 minutes
                "form_submit": {
                    "requests": 20,
                    "window": 60,
                },  # 20 form submissions per minute
            },
        )

    def process_request(self, request):
        if request.method not in ["POST", "PUT", "PATCH"]:
            return None

        # Get client IP
        ip = self.get_client_ip(request)
        if not ip:
            return None

        # Determine rate limit type based on URL
        limit_type = self.get_limit_type(request)
        rate_config = self.rate_limits.get(limit_type, self.rate_limits["default"])

        # Check rate limit
        if self.is_rate_limited(ip, limit_type, rate_config):
            return HttpResponse(
                "Rate limit exceeded. Please try again later.",
                content_type="text/plain",
                status=429,
            )

        return None

    def get_client_ip(self, request):
        """Get the client's IP address from request headers"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def get_limit_type(self, request):
        """Determine rate limit type based on request path"""
        path = request.path.lower()

        if "login" in path:
            return "login"
        elif "register" in path:
            return "register"
        elif any(keyword in path for keyword in ["upload", "import", "csv", "yaml"]):
            return "upload"
        elif request.method == "POST":
            return "form_submit"

        return "default"

    def is_rate_limited(self, ip, limit_type, rate_config):
        """Check if IP is rate limited for the given limit type"""
        cache_key = f"rate_limit:{limit_type}:{ip}"

        # Use dedicated rate limiting cache if available, otherwise default
        try:
            rate_cache = caches["ratelimit"]
        except:
            rate_cache = cache

        # Get current request count and timestamp
        data = rate_cache.get(cache_key, {"count": 0, "reset_time": time.time()})
        current_time = time.time()

        # Reset counter if time window has passed
        if current_time > data["reset_time"] + rate_config["window"]:
            data = {"count": 0, "reset_time": current_time}

        # Check if limit exceeded
        if data["count"] >= rate_config["requests"]:
            return True

        # Increment counter
        data["count"] += 1
        rate_cache.set(cache_key, data, rate_config["window"])

        return False


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses
    """

    def process_response(self, request, response):
        if not getattr(settings, "DEBUG", False):
            # Security headers for production
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            response["X-XSS-Protection"] = "1; mode=block"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

            # Content Security Policy
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' cdnjs.cloudflare.com cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
            response["Content-Security-Policy"] = csp

        return response
