"""
Sumatic Modern IoT - Configuration
Environment-based configuration with Pydantic Settings.
"""
from functools import lru_cache
from typing import Optional
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Sumatic Modern IoT"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sumatic_modern.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MQTT (Local - through SSH tunnel)
    MQTT_BROKER_HOST: str = "127.0.0.1"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_CLIENT_ID: str = "sumatic-backend"
    MQTT_TOPIC_ALLDATAS: str = "Alldatas"
    MQTT_TOPIC_COMMANDS: str = "Commands"
    
    # MQTT TLS/SSL Configuration
    MQTT_TLS_ENABLED: bool = False
    MQTT_TLS_PORT: int = 8883
    MQTT_TLS_CA_CERT: Optional[str] = None  # Path to CA certificate
    MQTT_TLS_CLIENT_CERT: Optional[str] = None  # Path to client certificate
    MQTT_TLS_CLIENT_KEY: Optional[str] = None  # Path to client private key
    MQTT_TLS_REQUIRE_CERT: bool = True  # Whether to require client certificate
    MQTT_TLS_INSECURE: bool = False  # Set to True only for testing with self-signed certs

    # SSH Tunnel Configuration
    SSH_ENABLED: bool = False
    SSH_HOST: str = "31.58.236.246"
    SSH_PORT: int = 22
    SSH_USER: str = "Administrator"
    SSH_PASSWORD: Optional[str] = None
    SSH_KEY_PATH: Optional[str] = None
    SSH_REMOTE_MQTT_HOST: str = "127.0.0.1"
    SSH_REMOTE_MQTT_PORT: int = 1883
    SSH_LOCAL_MQTT_HOST: str = "127.0.0.1"
    SSH_LOCAL_MQTT_PORT: int = 1883
    SSH_KEEPALIVE: int = 30

    # JWT Auth
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:8000,http://46.225.231.44:8001"
    RATE_LIMIT_PER_MINUTE: int = 100

    # Timezone
    TIMEZONE: str = "Europe/Istanbul"

    # Device monitoring
    DEVICE_OFFLINE_THRESHOLD_SECONDS: int = 600  # 10 minutes
    DEVICE_RETRY_INTERVAL_SECONDS: int = 60
    DEVICE_MAX_RETRIES: int = 5

    # Snapshot
    SNAPSHOT_INTERVAL_MINUTES: int = 10

    # Spike filter
    SPIKE_STREAK_THRESHOLD: int = 5
    SPIKE_WINDOW_SIZE: int = 5

    # Data Encryption at Rest
    # Base64-encoded 32-byte (256-bit) encryption key for sensitive data
    # Generate with: python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
    ENCRYPTION_KEY: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    settings = Settings()
    
    # Security validation
    if settings.JWT_SECRET_KEY == "change-this-to-a-secure-random-key-in-production":
        warnings.warn(
            "⚠️ SECURITY WARNING: JWT_SECRET_KEY is using the default insecure value! "
            "Set JWT_SECRET_KEY environment variable to a strong random string (min 32 characters) "
            "before deploying to production. Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            UserWarning,
            stacklevel=2
        )
    elif len(settings.JWT_SECRET_KEY) < 32:
        warnings.warn(
            "⚠️ SECURITY WARNING: JWT_SECRET_KEY is too short (less than 32 characters). "
            "Use a stronger random key for production. Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            UserWarning,
            stacklevel=2
        )
    
    if not settings.DEBUG and settings.SSH_PASSWORD:
        warnings.warn(
            "⚠️ SECURITY WARNING: SSH_PASSWORD is set in production (DEBUG=False). "
            "Migrate to SSH key-based authentication for better security. "
            "Generate SSH key with: ssh-keygen -t ed25519 -f ~/.ssh/sumatic_tunnel_key",
            UserWarning,
            stacklevel=2
        )
    
    if not settings.DEBUG:
        # Check for localhost in CORS origins in production
        cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
        localhost_origins = [origin for origin in cors_origins if "localhost" in origin.lower() or "127.0.0.1" in origin]
        if localhost_origins:
            warnings.warn(
                f"⚠️ SECURITY WARNING: Localhost origins found in CORS_ORIGINS in production (DEBUG=False): {localhost_origins}. "
                "Remove localhost origins and use only production domains.",
                UserWarning,
                stacklevel=2
            )
        
        # Check if using SQLite in production
        if settings.DATABASE_URL.startswith("sqlite"):
            warnings.warn(
                "⚠️ SECURITY WARNING: Using SQLite in production (DEBUG=False). "
                "SQLite is not suitable for production. Migrate to PostgreSQL for better performance, concurrency, and security.",
                UserWarning,
                stacklevel=2
            )
    
    return settings
