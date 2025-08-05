from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load .env file at module import
load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "DeepSeaGuard Compliance Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=1, env="WORKERS")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./deepseaguard.db",
        env="DATABASE_URL"
    )
    DATABASE_SYNC_URL: str = Field(
        default="sqlite:///./deepseaguard.db",
        env="DATABASE_SYNC_URL"
    )
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 30 * 60  # 30 minutes
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    
    # Cache
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # 5 minutes
    CACHE_PREFIX: str = "deepseaguard"
    
    # Geo-fencing
    GEO_CACHE_TTL: int = Field(default=3600, env="GEO_CACHE_TTL")  # 1 hour
    MAX_ZONE_SIZE_MB: int = Field(default=10, env="MAX_ZONE_SIZE_MB")
    
    # Compliance
    VIOLATION_CHECK_INTERVAL: int = Field(default=60, env="VIOLATION_CHECK_INTERVAL")  # seconds
    WARNING_THRESHOLD_PERCENT: float = Field(default=80.0, env="WARNING_THRESHOLD_PERCENT")
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")  # seconds
    WS_MAX_CONNECTIONS: int = Field(default=1000, env="WS_MAX_CONNECTIONS")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    
    # File upload
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

# Function to get settings instance
def get_settings() -> Settings:
    """Get settings instance with proper .env loading"""
    return Settings()

# Global settings instance
settings = get_settings()

# Environment-specific settings
class DevelopmentSettings(Settings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Use SQLite for development
    DATABASE_URL: str = "sqlite+aiosqlite:///./deepseaguard_dev.db"
    DATABASE_SYNC_URL: str = "sqlite:///./deepseaguard_dev.db"

class ProductionSettings(Settings):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    CORS_ORIGINS: List[str] = []  # Set specific origins in production
    # Can use either SQLite or PostgreSQL in production
    # DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/deepseaguard"
    # DATABASE_SYNC_URL: str = "postgresql://user:password@localhost/deepseaguard"

class TestingSettings(Settings):
    DEBUG: bool = True
    # Use in-memory SQLite for testing
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    DATABASE_SYNC_URL: str = "sqlite:///:memory:"
    REDIS_URL: str = "redis://localhost:6379/15"
    CELERY_BROKER_URL: str = "redis://localhost:6379/16" 