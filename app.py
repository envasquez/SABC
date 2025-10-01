import uvicorn

from app_routes import register_routes
from app_setup import create_app

app = create_app()
register_routes(app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)  # type: ignore[misc]
