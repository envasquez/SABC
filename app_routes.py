from fastapi import FastAPI

from routes import api, auth, monitoring, pages, password_reset, photos, static, tournaments, voting
from routes.admin import core as admin_core
from routes.admin import events as admin_events
from routes.admin import lakes as admin_lakes
from routes.admin import polls as admin_polls
from routes.admin import tournaments as admin_tournaments
from routes.admin import users as admin_users


def register_routes(app: FastAPI) -> None:
    # Monitoring endpoints (metrics, health checks)
    app.include_router(monitoring.router)
    app.include_router(auth.router)
    app.include_router(password_reset.router)
    # Register specific admin routes BEFORE the catch-all admin_core.router
    app.include_router(admin_lakes.router)
    app.include_router(admin_events.router)
    app.include_router(admin_polls.router)
    app.include_router(admin_tournaments.router)
    app.include_router(admin_users.router)
    # Register catch-all /admin/{page} route LAST among admin routes
    app.include_router(admin_core.router)
    app.include_router(api.router)
    app.include_router(static.router)
    app.include_router(voting.router)
    app.include_router(tournaments.router)
    app.include_router(photos.router)
    app.include_router(pages.router)
