# Health check endpoints and monitoring utilities
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache, caches
from django.core.mail import mail_admins
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


class HealthCheckRunner:
    """
    Health check system for monitoring application components.
    """

    @classmethod
    def run_all_checks(cls) -> Dict[str, Any]:
        """Run all health checks and return results."""
        checks = {
            "database": cls.check_database(),
            "cache": cls.check_cache(),
            "email": cls.check_email(),
            "static_files": cls.check_static_files(),
            "disk_space": cls.check_disk_space(),
            "memory": cls.check_memory(),
        }

        # Overall health status
        all_healthy = all(check["healthy"] for check in checks.values())

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
            "version": getattr(settings, "VERSION", "unknown"),
            "environment": "production" if not settings.DEBUG else "development",
        }

    @classmethod
    def check_database(cls) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        start_time = time.time()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            response_time = time.time() - start_time

            return {
                "healthy": True,
                "response_time_ms": round(response_time * 1000, 2),
                "message": "Database connection successful",
            }

        except Exception as e:
            return {
                "healthy": False,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "message": f"Database connection failed: {str(e)}",
                "error": type(e).__name__,
            }

    @classmethod
    def check_cache(cls) -> Dict[str, Any]:
        """Check cache systems (default, sessions, rate limiting)."""
        cache_results = {}
        overall_healthy = True

        # Check default cache
        cache_results["default"] = cls._check_single_cache("default")
        if not cache_results["default"]["healthy"]:
            overall_healthy = False

        # Check session cache if configured
        try:
            session_cache = caches["sessions"]
            cache_results["sessions"] = cls._check_single_cache("sessions")
            if not cache_results["sessions"]["healthy"]:
                overall_healthy = False
        except:
            cache_results["sessions"] = {"healthy": True, "message": "Not configured"}

        # Check rate limiting cache if configured
        try:
            rate_cache = caches["ratelimit"]
            cache_results["ratelimit"] = cls._check_single_cache("ratelimit")
            if not cache_results["ratelimit"]["healthy"]:
                overall_healthy = False
        except:
            cache_results["ratelimit"] = {"healthy": True, "message": "Not configured"}

        return {
            "healthy": overall_healthy,
            "caches": cache_results,
            "message": "All caches operational"
            if overall_healthy
            else "Some cache issues detected",
        }

    @classmethod
    def _check_single_cache(cls, cache_name: str) -> Dict[str, Any]:
        """Check a single cache backend."""
        start_time = time.time()
        test_key = f"health_check_{cache_name}_{int(time.time())}"
        test_value = "health_check_value"

        try:
            if cache_name == "default":
                cache_backend = cache
            else:
                cache_backend = caches[cache_name]

            # Test set and get operations
            cache_backend.set(test_key, test_value, 60)
            retrieved_value = cache_backend.get(test_key)
            cache_backend.delete(test_key)

            response_time = time.time() - start_time

            if retrieved_value == test_value:
                return {
                    "healthy": True,
                    "response_time_ms": round(response_time * 1000, 2),
                    "message": f"{cache_name.capitalize()} cache operational",
                }
            else:
                return {
                    "healthy": False,
                    "response_time_ms": round(response_time * 1000, 2),
                    "message": f"{cache_name.capitalize()} cache data integrity issue",
                }

        except Exception as e:
            return {
                "healthy": False,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "message": f"{cache_name.capitalize()} cache error: {str(e)}",
                "error": type(e).__name__,
            }

    @classmethod
    def check_email(cls) -> Dict[str, Any]:
        """Check email system configuration."""
        try:
            from django.core.mail import get_connection

            connection = get_connection()
            # Don't actually send email, just check connection
            # connection.open()
            # connection.close()

            return {
                "healthy": True,
                "message": "Email backend configured",
                "backend": settings.EMAIL_BACKEND,
            }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Email system error: {str(e)}",
                "error": type(e).__name__,
            }

    @classmethod
    def check_static_files(cls) -> Dict[str, Any]:
        """Check static file configuration."""
        try:
            import os

            static_root = getattr(settings, "STATIC_ROOT", "")
            static_url = getattr(settings, "STATIC_URL", "/static/")

            if settings.DEBUG:
                return {
                    "healthy": True,
                    "message": "Static files served by Django (DEBUG mode)",
                    "static_url": static_url,
                }

            elif static_root and os.path.exists(static_root):
                # Count files in static root
                file_count = sum(len(files) for _, _, files in os.walk(static_root))
                return {
                    "healthy": True,
                    "message": f"Static files collected ({file_count} files)",
                    "static_root": static_root,
                    "static_url": static_url,
                    "file_count": file_count,
                }

            else:
                return {
                    "healthy": False,
                    "message": "Static files not properly configured or collected",
                    "static_root": static_root,
                }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Static files check error: {str(e)}",
                "error": type(e).__name__,
            }

    @classmethod
    def check_disk_space(cls) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            import shutil

            base_dir = settings.BASE_DIR
            total, used, free = shutil.disk_usage(base_dir)

            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total) * 100

            # Alert if usage is over 90%
            healthy = usage_percent < 90

            return {
                "healthy": healthy,
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round(usage_percent, 2),
                "message": f"Disk usage: {usage_percent:.1f}%"
                + (" - WARNING: High disk usage" if not healthy else ""),
            }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Disk space check error: {str(e)}",
                "error": type(e).__name__,
            }

    @classmethod
    def check_memory(cls) -> Dict[str, Any]:
        """Check memory usage (if psutil is available)."""
        try:
            import psutil  # type: ignore[import-untyped]

            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            available_gb = memory.available / (1024**3)

            # Alert if usage is over 90%
            healthy = usage_percent < 90

            return {
                "healthy": healthy,
                "usage_percent": round(usage_percent, 2),
                "available_gb": round(available_gb, 2),
                "total_gb": round(memory.total / (1024**3), 2),
                "message": f"Memory usage: {usage_percent:.1f}%"
                + (" - WARNING: High memory usage" if not healthy else ""),
            }

        except ImportError:
            return {
                "healthy": True,
                "message": "Memory monitoring not available (psutil not installed)",
            }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Memory check error: {str(e)}",
                "error": type(e).__name__,
            }


@method_decorator(never_cache, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class HealthCheckView(View):
    """
    Health check endpoint for monitoring systems.
    Returns JSON with health status of all components.
    """

    def get(self, request):
        """Return detailed health check results."""
        health_data = HealthCheckRunner.run_all_checks()

        # Return appropriate HTTP status
        status_code = 200 if health_data["status"] == "healthy" else 503

        return JsonResponse(
            health_data, status=status_code, json_dumps_params={"indent": 2}
        )


@method_decorator(never_cache, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class ReadinessCheckView(View):
    """
    Readiness check for Kubernetes/Docker deployments.
    Returns simple OK/FAIL response.
    """

    def get(self, request):
        """Return simple readiness check."""
        try:
            # Quick database check
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            # Quick cache check
            test_key = f"readiness_{int(time.time())}"
            cache.set(test_key, "ok", 10)
            if cache.get(test_key) == "ok":
                cache.delete(test_key)
                return HttpResponse("OK", content_type="text/plain")
            else:
                return HttpResponse(
                    "FAIL - Cache", status=503, content_type="text/plain"
                )

        except Exception as e:
            return HttpResponse(
                f"FAIL - {str(e)}", status=503, content_type="text/plain"
            )


@method_decorator(never_cache, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class LivenessCheckView(View):
    """
    Liveness check for Kubernetes/Docker deployments.
    Returns simple response if application is running.
    """

    def get(self, request):
        """Return simple liveness response."""
        return HttpResponse("OK", content_type="text/plain")


def scheduled_health_check():
    """
    Function to be called by a scheduled task (cron, celery, etc.)
    to monitor application health and send alerts if needed.
    """
    if settings.DEBUG:
        return  # Skip in development

    health_data = HealthCheckRunner.run_all_checks()

    # Check if we need to send alerts
    if health_data["status"] != "healthy":
        # Check if we've already alerted recently to avoid spam
        alert_key = "health_check_alert"
        last_alert = cache.get(alert_key)

        if last_alert is None:
            # Send alert
            subject = "[SABC] Health Check Alert - System Unhealthy"

            message_parts = [
                f"Health check failed at {health_data['timestamp']}",
                f"Overall status: {health_data['status']}",
                "\nFailed checks:",
            ]

            for check_name, check_data in health_data["checks"].items():
                if not check_data["healthy"]:
                    message_parts.append(f"- {check_name}: {check_data['message']}")

            message = "\n".join(message_parts)

            try:
                mail_admins(subject, message, fail_silently=True)
                # Set alert cooldown for 1 hour
                cache.set(alert_key, datetime.now().isoformat(), 3600)
                logger.warning(f"Health check alert sent: {health_data['status']}")
            except Exception as e:
                logger.error(f"Failed to send health check alert: {e}")

    else:
        # System is healthy, clear any alert cooldown
        cache.delete("health_check_alert")

    return health_data
