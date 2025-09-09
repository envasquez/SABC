"""Static routes for favicon and catch-all pages."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .dependencies import *

router = APIRouter()


@router.get("/favicon.ico")
@router.get("/apple-touch-icon{path:path}.png")
async def icons():
    return Response(open("static/favicon.svg").read(), media_type="image/svg+xml")


@router.get("/{page:path}")
async def page(request: Request, page: str = "", p: int = 1):
    """Catch-all route for static pages."""
    user = u(request)
    if page in ["", "about", "bylaws", "awards"]:
        # Use home page for the root route
        if not page:
            # Import here to avoid circular import
            from .calendar import home_paginated

            return await home_paginated(request, p)

        # For other static pages, use simple template
        t = f"{page}.html"
        ctx = {"request": request, "user": user}
        return templates.TemplateResponse(t, ctx)
    # Return 404 for unknown pages
    raise HTTPException(status_code=404, detail="Page not found")
