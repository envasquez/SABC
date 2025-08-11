"""
Custom context processors for the SABC application.

These context processors add variables to all template contexts
across the application.
"""

from django.conf import settings


def staging_context(request):
    """
    Add staging-specific context variables to all templates.

    Args:
        request: Django HttpRequest object

    Returns:
        Dictionary of context variables for templates
    """
    context = {}

    # Add staging environment indicator
    if getattr(settings, "STAGING_ENVIRONMENT", False):
        context.update(
            {
                "is_staging": True,
                "staging_banner_message": getattr(
                    settings, "STAGING_BANNER_MESSAGE", "This is a staging environment"
                ),
                "environment_name": "Staging",
                "environment_color": "#ff9800",  # Orange color for staging banner
            }
        )
    else:
        context.update(
            {
                "is_staging": False,
                "environment_name": "Production",
            }
        )

    # Add version information if available
    context["app_version"] = getattr(settings, "APP_VERSION", "dev")

    # Add debug information
    context["debug_mode"] = getattr(settings, "DEBUG", False)

    return context


def app_metadata(request):
    """
    Add application metadata to all templates.

    Args:
        request: Django HttpRequest object

    Returns:
        Dictionary of application metadata for templates
    """
    return {
        "app_name": "SABC Tournament Management",
        "app_short_name": "SABC",
        "current_year": 2024,  # TODO: Make this dynamic
        "support_email": getattr(settings, "SUPPORT_EMAIL", "admin@sabc.com"),
    }
