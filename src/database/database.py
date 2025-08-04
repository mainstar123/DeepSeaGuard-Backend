from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
import os
from src.config.settings import settings

# Database configuration
def get_database_url():
    """Get database URL based on configuration"""
    return settings.DATABASE_URL

def get_sync_database_url():
    """Get synchronous database URL for migrations and sync operations"""
    return settings.DATABASE_SYNC_URL

# Create async engine for FastAPI
async_engine = create_async_engine(
    get_database_url(),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if "sqlite" in get_database_url() else {}
)

# Create sync engine for migrations and Celery tasks
sync_engine = create_engine(
    get_sync_database_url(),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if "sqlite" in get_sync_database_url() else {}
)

# Session makers
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=sync_engine
)

Base = declarative_base()

class ComplianceEvent(Base):
    __tablename__ = "compliance_events"
    
    id = Column(Integer, primary_key=True, index=True)
    auv_id = Column(String, index=True)
    zone_id = Column(String, index=True)
    zone_name = Column(String)
    event_type = Column(String)  # "entry", "exit", "violation", "warning"
    status = Column(String)  # "compliant", "warning", "violation"
    latitude = Column(Float)
    longitude = Column(Float)
    depth = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_minutes = Column(Float, nullable=True)
    violation_details = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

class AUVZoneTracking(Base):
    __tablename__ = "auv_zone_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    auv_id = Column(String, index=True)
    zone_id = Column(String, index=True)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    total_duration_minutes = Column(Float, default=0)
    is_active = Column(Boolean, default=True)

class ISAZone(Base):
    __tablename__ = "isa_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, unique=True, index=True)
    zone_name = Column(String)
    zone_type = Column(String)  # "sensitive", "restricted", "protected"
    max_duration_hours = Column(Float)
    geojson_data = Column(Text)
    is_active = Column(Boolean, default=True)

# Async database dependency for FastAPI
async def get_async_db():
    """Async database session for FastAPI endpoints"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Sync database dependency for Celery tasks and migrations
def get_db():
    """Synchronous database session for Celery tasks and migrations"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database initialization
async def init_async_db():
    """Initialize async database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def init_sync_db():
    """Initialize sync database tables"""
    Base.metadata.create_all(bind=sync_engine)

# Database health check
async def check_async_db_health():
    """Check async database health"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception:
        return False

def check_sync_db_health():
    """Check sync database health"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception:
        return False 