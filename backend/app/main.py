"""
Sumatic Modern IoT - Main Application
FastAPI application factory with startup/shutdown events.
Integrated with SSH tunnel for remote MQTT broker access.
"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging, get_logger
from app.api.router import create_api_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.api_security import APISecurityMiddleware, ResponseFilterMiddleware

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # ─── STARTUP ──────────────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Start SSH tunnel if enabled
    if settings.SSH_ENABLED:
        try:
            from app.services.ssh_tunnel import get_ssh_tunnel
            ssh_tunnel = get_ssh_tunnel()
            tunnel_started = await ssh_tunnel.start()
            if tunnel_started:
                logger.info("[OK] SSH tunnel established successfully")
            else:
                logger.error("[ERROR] Failed to establish SSH tunnel")
        except Exception as e:
            logger.error(f"[ERROR] SSH tunnel start error: {e}")
    
    # Initialize database
    from app.database import init_db
    try:
        await init_db()
        logger.info("[OK] Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        # Continue anyway - tables might already exist via Alembic
    
    # Create admin user from environment variables
    try:
        from app.database import async_session_maker
        from app.models.user import User
        from app.core.security import get_password_hash
        from sqlalchemy import select
        import os
        
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@sumatic.io")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.username == admin_username)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                admin = User(
                    username=admin_username,
                    email=admin_email,
                    password_hash=get_password_hash(admin_password),
                    full_name="Admin User",
                    role="admin",
                    is_active=True,
                )
                session.add(admin)
                await session.commit()
                logger.info(f"[OK] Admin user created: {admin_username}")
            else:
                logger.info(f"[OK] Admin user already exists: {admin_username}")
    except Exception as e:
        logger.warning(f"[WARN] Admin user creation skipped: {e}")
    
    # Fix status case: ONLINE/OFFLINE/PARTIAL -> online/offline/partial
    try:
        from app.database import async_session_maker
        from sqlalchemy import text
        
        async with async_session_maker() as session:
            result = await session.execute(text(
                "UPDATE device_readings SET status = LOWER(status) WHERE status IN ('ONLINE','OFFLINE','PARTIAL')"
            ))
            await session.commit()
            if result.rowcount > 0:
                logger.info(f"[OK] Fixed status case for {result.rowcount} device_readings")
    except Exception as e:
        logger.warning(f"[WARN] Status case fix skipped: {e}")
    
    # Ensure register definitions exist (seed if empty)
    try:
        from app.database import async_session_maker
        from app.models.register_definition import RegisterDefinition
        from sqlalchemy import select
        
        async with async_session_maker() as session:
            result = await session.execute(select(RegisterDefinition))
            existing_regs = result.scalars().all()
            
            if len(existing_regs) == 0:
                # Add default register definitions
                registers = [
                    (3, 100, "Sıcaklık"), (3, 101, "Nem"), (3, 102, "Basınç"),
                    (3, 1000, "Sıcaklık 1"), (3, 1001, "Sıcaklık 2"), (3, 1002, "Sıcaklık 3"),
                    (3, 1003, "Sıcaklık 4"), (3, 1004, "Sıcaklık 5"), (3, 1005, "Sıcaklık 6"),
                    (3, 1006, "Sıcaklık 7"), (3, 1007, "Sıcaklık 8"), (3, 1453, "Diğer 1"),
                    (4, 2000, "Sayac 1"), (4, 2001, "Sayac 2"), (4, 2002, "Çıkış-1 Durum"),
                    (4, 2003, "Çıkış-2 Durum"), (4, 2004, "Acil Arıza Durumu"),
                    (4, 2005, "Sayac Toplam Low16"), (4, 2006, "Sayac Toplam High16"),
                ]
                for fc, reg, name in registers:
                    session.add(RegisterDefinition(fc=fc, reg=reg, name=name))
                await session.commit()
                logger.info(f"[OK] Seeded {len(registers)} register definitions")
            else:
                logger.info(f"[OK] Register definitions found: {len(existing_regs)} entries")
    except Exception as e:
        logger.warning(f"[WARN] Register definition seeding skipped: {e}")
    
    # Initialize Redis
    from app.redis_client import get_redis
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("[OK] Redis connection established")
    except Exception as e:
        logger.warning(f"[WARN] Redis connection failed: {e}")
    
    # Start MQTT consumer
    try:
        from app.services.mqtt_consumer import get_mqtt_consumer
        mqtt_consumer = get_mqtt_consumer()
        await mqtt_consumer.start()
        logger.info("[OK] MQTT consumer started")
    except Exception as e:
        logger.error(f"[ERROR] MQTT consumer start error: {e}")
    
    logger.info(f"[OK] {settings.APP_NAME} started successfully")
    
    yield
    
    # ─── SHUTDOWN ─────────────────────────────────────────────────────
    logger.info("Shutting down application...")
    
    # Stop SSH tunnel
    if settings.SSH_ENABLED:
        try:
            from app.services.ssh_tunnel import get_ssh_tunnel
            ssh_tunnel = get_ssh_tunnel()
            await ssh_tunnel.stop()
            logger.info("[OK] SSH tunnel stopped")
        except Exception as e:
            logger.error(f"SSH tunnel stop error: {e}")
    
    # Stop MQTT consumer
    try:
        from app.services.mqtt_consumer import get_mqtt_consumer
        mqtt_consumer = get_mqtt_consumer()
        await mqtt_consumer.stop()
        logger.info("[OK] MQTT consumer stopped")
    except Exception as e:
        logger.error(f"MQTT consumer stop error: {e}")
    
    # Close Redis
    from app.redis_client import close_redis
    try:
        await close_redis()
        logger.info("[OK] Redis connection closed")
    except Exception as e:
        logger.error(f"Redis close error: {e}")
    
    # Close database
    from app.database import close_db
    try:
        await close_db()
        logger.info("[OK] Database connections closed")
    except Exception as e:
        logger.error(f"Database close error: {e}")
    
    logger.info("[OK] Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # API docs only in DEBUG mode (disabled in production)
    docs_url = "/docs" if settings.DEBUG else None
    redoc_url = "/redoc" if settings.DEBUG else None
    openapi_url = "/openapi.json" if settings.DEBUG else None

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Sumatic Modern IoT Platform API - Device monitoring, analytics, and management",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    
    # ─── CORS Middleware ──────────────────────────────────────────────
    cors_origins = [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"],
    )
    
    # ─── Rate Limiting Middleware ─────────────────────────────────────
    app.add_middleware(RateLimitMiddleware)
    
    # ─── Security Headers Middleware ─────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    
    # ─── Request Size Limit Middleware ───────────────────────────────
    # Prevents large payload attacks (DDoS, memory exhaustion)
    # Disabled in DEBUG mode for development convenience
    app.add_middleware(RequestSizeLimitMiddleware)
    
    # ─── API Security Middleware ──────────────────────────────────────
    # Add security headers and filter sensitive data from API responses
    app.add_middleware(ResponseFilterMiddleware)
    app.add_middleware(APISecurityMiddleware)
    
    # ─── Exception Handlers ──────────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application-specific exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
                "status_code": exc.status_code,
            },
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Handle unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "status_code": 500,
            },
        )
    
    # ─── Include API Router ──────────────────────────────────────────
    api_router = create_api_router()
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # ─── Health Check ─────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint with all service statuses."""
        health = {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Check database
        try:
            from app.database import async_session_maker
            from sqlalchemy import text
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            health["database"] = "connected"
        except Exception as e:
            health["database"] = f"error: {str(e)}"
            health["status"] = "degraded"
        
        # Check Redis
        try:
            from app.redis_client import get_redis
            redis = await get_redis()
            await redis.ping()
            health["redis"] = "connected"
        except Exception as e:
            health["redis"] = f"error: {str(e)}"
            health["status"] = "degraded"
        
        # Check SSH Tunnel
        if settings.SSH_ENABLED:
            try:
                from app.services.ssh_tunnel import get_ssh_tunnel
                ssh_tunnel = get_ssh_tunnel()
                tunnel_status = ssh_tunnel.get_status()
                health["ssh_tunnel"] = {
                    "active": tunnel_status.get("active"),
                    "running": tunnel_status.get("running"),
                    "remote_host": tunnel_status.get("remote_host"),
                    "local_port": tunnel_status.get("local_port"),
                }
                if not tunnel_status.get("active"):
                    health["status"] = "degraded"
            except Exception as e:
                health["ssh_tunnel"] = f"error: {str(e)}"
        
        # Check MQTT
        try:
            from app.services.mqtt_consumer import get_mqtt_consumer
            mqtt_consumer = get_mqtt_consumer()
            mqtt_status = mqtt_consumer.get_status()
            health["mqtt"] = {
                "running": mqtt_status.get("running"),
                "connected": mqtt_status.get("connected"),
                "broker_host": mqtt_status.get("broker_host"),
                "broker_port": mqtt_status.get("broker_port"),
                "known_modems": mqtt_status.get("known_modems"),
                "device_configs": mqtt_status.get("device_configs"),
            }
            if not mqtt_status.get("connected"):
                health["status"] = "degraded"
        except Exception as e:
            health["mqtt"] = f"error: {str(e)}"
        
        return health
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
            "api": f"{settings.API_V1_PREFIX}",
        }
    
    return app


# Create the application instance
app = create_app()
