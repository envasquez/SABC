from fastapi import FastAPI

from routes import api, auth, pages, password_reset, static, tournaments, voting
from routes.admin import core as admin_core
from routes.admin import events as admin_events
from routes.admin import lakes as admin_lakes
from routes.admin import polls as admin_polls
from routes.admin import tournaments as admin_tournaments
from routes.admin import users as admin_users


def register_routes(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(password_reset.router)
    app.include_router(admin_lakes.router)
    app.include_router(admin_core.router)
    app.include_router(admin_events.router)
    app.include_router(admin_polls.router)
    app.include_router(admin_tournaments.router)
    app.include_router(admin_users.router)
    app.include_router(api.router)
    app.include_router(static.router)
    app.include_router(voting.router)
    app.include_router(tournaments.router)
    app.include_router(pages.router)
