"""
FastAPI application entrypoint for VyRaTrader (Production Ready).
- Initializes database and optional background scheduler on startup; stops on shutdown.
- Registers all API v1 routers and configures CORS from environment-based settings.
- Ensures the /api/v1/signals router is mounted so frontend can fetch signals.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import init_db 

# import routers
from backend.app.api.v1 import auth as auth_router
from backend.app.api.v1 import users as users_router
from backend.app.api.v1 import payments as payments_router
from backend.app.api.v1 import webhooks as webhooks_router
from backend.app.api.v1 import trades as trades_router
from backend.app.api.v1 import portfolio as portfolio_router
from backend.app.api.v1 import ai as ai_router
from backend.app.api.v1 import notifications as notifications_router
from backend.app.api.v1 import system as system_router
from backend.app.api.v1 import brokers as brokers_router
from backend.app.api.v1 import ops as ops_router
from backend.app.api.v1 import legal as legal_router
from backend.app.api.v1 import market as market_router
from backend.app.db.session import engine
from sqlmodel import SQLModel
import os


# Ensure signals router is imported and mounted
try:
    from backend.app.api.v1 import signals as signals_router
except Exception:
    signals_router = None

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="AI-Powered Trading Platform API",
        docs_url="/api/docs" if settings.ENV != "production" else None,
        redoc_url="/api/redoc" if settings.ENV != "production" else None,
    )

    # CORS Configuration - Environment-based origins
    # For production, set ALLOWED_ORIGINS env variable with comma-separated domains
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
    
    if os.getenv("ENV") == "production":
        # Production: only allow specific domains
        origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
        if not origins:
            # Fallback production domains
            origins = [
                "https://vyratrader.com",
                "https://www.vyratrader.com",
                "https://app.vyratrader.com",
                "https://api.vyratrader.com",
            ]
    else:
        # Development/Staging: allow all localhost and 127.0.0.1 origins
        origins = ["*"]  # Allow all origins in development
        # Add custom origins from env if provided
        if allowed_origins_env:
            origins.extend([origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()])

    logger.info(f"CORS enabled for origins: {origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Mx-ReqToken",
            "Keep-Alive",
            "X-Requested-With",
            "If-Modified-Since",
            "X-CSRF-Token",
        ],
        expose_headers=["Content-Length", "X-Request-ID"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Add global OPTIONS handler for CORS preflight BEFORE including routers
    app.router.redirect_slashes = False  # Disable automatic redirect for OPTIONS

    @app.middleware("http")
    async def global_options_middleware(request, call_next):
        # Handle OPTIONS preflight before anything else
        if request.method == "OPTIONS":
            response = JSONResponse({})
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = request.headers.get(
                "access-control-request-headers", 
                "Authorization, Content-Type, Accept, Origin, X-Requested-With"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        return await call_next(request)
    

    # Security Headers Middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ✅ Register all routers with correct /api/v1 prefixes
    app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(users_router.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(payments_router.router, prefix="/api/v1/payments", tags=["Payments"])
    app.include_router(webhooks_router.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
    app.include_router(trades_router.router, prefix="/api/v1/trades", tags=["Trades"])
    app.include_router(portfolio_router.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
    app.include_router(ai_router.router, prefix="/api/v1/ai", tags=["AI"])
    app.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["Notifications"])
    app.include_router(system_router.router, prefix="/api/v1/system", tags=["System"])
    app.include_router(brokers_router.router, prefix="/api/v1/brokers", tags=["Brokers"])
    app.include_router(ops_router.router, prefix="/api/v1/ops", tags=["Operations"])
    app.include_router(legal_router.router, prefix="/api/v1/legal", tags=["Legal"])
    app.include_router(market_router.router, prefix="/api/v1/market", tags=["Market"])

    # ✅ Mount signals router if available
    if signals_router is not None:
        app.include_router(signals_router.router, prefix="/api/v1", tags=["Signals"])

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        return {
            "service": "VyRaTrader API",
            "version": "1.0.0",
            "status": "operational",
            "environment": os.getenv("ENV", "development"),
        }

    @app.get("/health", tags=["System"])
    async def health() -> dict:
        return {
            "status": "healthy",
            "service": "VyRaTrader API",
            "version": "1.0.0"
        }

    @app.get("/api/v1/health", tags=["System"])
    async def api_health() -> dict:
        return {
            "status": "healthy",
            "api_version": "v1",
            "service": "VyRaTrader"
        }

    return app


app = create_app()

@app.on_event("startup")
async def _startup():
    logger.info("VyRaTrader starting up - initializing DB and schedulers")
    try:
        # Async-safe table creation (no blocking create_all on AsyncEngine)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.exception(f"DB init failed: {e}")
        raise  # Fail fast in production

    # Start background collectors if scheduler exists
    try:
        from backend.app.services.scheduler import start_background_tasks

        collection_interval = int(os.getenv("COLLECTION_INTERVAL", "30"))
        start_background_tasks(app, interval_seconds=collection_interval)
        logger.info(f"✅ Background tasks started (interval={collection_interval}s)")
    except Exception as e:
        logger.warning(f"Could not start background tasks: {e}")


@app.on_event("shutdown")
async def _shutdown():
    logger.info("VyRaTrader shutting down gracefully")
    # Add cleanup tasks here if needed
    try:
        # Close database connections
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("ENV") != "production"

    logger.info(f"Starting VyRaTrader API on {host}:{port}")
    
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info" if os.getenv("ENV") == "production" else "debug",
        access_log=True,
    )