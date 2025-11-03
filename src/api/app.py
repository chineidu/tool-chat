import sys
import warnings

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api import lifespan
from src.api.routes import admin, auth, feedback, health, history, streamer
from src.config import app_config

warnings.filterwarnings("ignore")


def create_application() -> FastAPI:
    """Create and configure a FastAPI application instance.

    This function initializes a FastAPI application with custom configuration settings,
    adds CORS middleware, and includes API route handlers.

    Returns
    -------
    FastAPI
        A configured FastAPI application instance.
    """
    prefix = app_config.api_config.prefix
    auth_prefix: str = app_config.api_config.auth_prefix

    app = FastAPI(
        title="My Demo API",
        description="API for my demo application",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.api_config.middleware.cors.allow_origins,
        allow_credentials=app_config.api_config.middleware.cors.allow_credentials,
        allow_methods=app_config.api_config.middleware.cors.allow_methods,
        allow_headers=app_config.api_config.middleware.cors.allow_headers,
    )

    # Include routers
    app.include_router(auth.router, prefix=auth_prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(feedback.router, prefix=prefix)
    app.include_router(health.router, prefix=prefix)
    app.include_router(streamer.router, prefix=prefix)
    app.include_router(history.router, prefix=prefix)

    # Add exception handlers
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    return app


app: FastAPI = create_application()

if __name__ == "__main__":
    try:
        uvicorn.run(
            "src.api.app:app",
            host=app_config.api_config.server.host,
            port=app_config.api_config.server.port,
            reload=app_config.api_config.server.reload,
        )
    except (Exception, KeyboardInterrupt) as e:
        print(f"Error creating application: {e}")
        print("Exiting gracefully...")
        sys.exit(1)
