#!/usr/bin/env python3
"""
Python installation script for DeepSeaGuard
Handles dependency installation with error handling
"""

import subprocess
import sys
import os
import platform

def run_pip_install(package, description=""):
    """Install a single package with error handling"""
    if description:
        print(f"📦 Installing {description}...")
    else:
        print(f"📦 Installing {package}...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e.stderr}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ["logs", "uploads", "backups"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")

def create_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists(".env"):
        env_content = """# DeepSeaGuard Environment Configuration

# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./deepseaguard.db
DATABASE_SYNC_URL=sqlite:///./deepseaguard.db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development
DEBUG=true
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        print("📄 Created .env file with default configuration")

def main():
    """Main installation function"""
    print("🚀 DeepSeaGuard Python Installation")
    print("=" * 40)
    
    # Check Python version
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    
    # Upgrade pip first
    print("🔄 Upgrading pip...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        print("✅ Pip upgraded successfully")
    except subprocess.CalledProcessError:
        print("⚠️ Failed to upgrade pip, continuing...")
    
    # Core packages
    core_packages = [
        ("fastapi==0.104.1", "FastAPI"),
        ('"uvicorn[standard]==0.24.0"', "Uvicorn"),
        ("python-multipart==0.0.6", "Python Multipart"),
        ("python-dotenv==1.0.0", "Python Dotenv"),
    ]
    
    print("\n📦 Installing core packages...")
    for package, description in core_packages:
        run_pip_install(package, description)
    
    # Database packages
    db_packages = [
        ("sqlalchemy==2.0.23", "SQLAlchemy"),
        ("aiosqlite==0.19.0", "Async SQLite"),
    ]
    
    print("\n🗄️ Installing database packages...")
    for package, description in db_packages:
        run_pip_install(package, description)
    
    # Background task packages
    task_packages = [
        ("celery==5.3.4", "Celery"),
        ("redis==5.0.1", "Redis"),
    ]
    
    print("\n⚡ Installing background task packages...")
    for package, description in task_packages:
        run_pip_install(package, description)
    
    # Geo processing packages (install numpy first)
    geo_packages = [
        ("numpy==1.25.2", "NumPy"),
        ("shapely==2.0.2", "Shapely"),
        ("geojson==3.1.0", "GeoJSON"),
    ]
    
    print("\n🗺️ Installing geo processing packages...")
    for package, description in geo_packages:
        run_pip_install(package, description)
    
    # Validation packages
    validation_packages = [
        ("pydantic==2.5.0", "Pydantic"),
        ("pydantic-settings==2.1.0", "Pydantic Settings"),
    ]
    
    print("\n✅ Installing validation packages...")
    for package, description in validation_packages:
        run_pip_install(package, description)
    
    # Async packages
    async_packages = [
        ("httpx==0.25.2", "HTTPX"),
        ("websockets==12.0", "WebSockets"),
        ("aiofiles==23.2.1", "Async Files"),
    ]
    
    print("\n🔄 Installing async packages...")
    for package, description in async_packages:
        run_pip_install(package, description)
    
    # Caching packages
    cache_packages = [
        ("aioredis==2.0.1", "Async Redis"),
    ]
    
    print("\n💾 Installing caching packages...")
    for package, description in cache_packages:
        run_pip_install(package, description)
    
    # Logging packages
    logging_packages = [
        ("structlog==23.2.0", "Structured Logging"),
    ]
    
    print("\n📝 Installing logging packages...")
    for package, description in logging_packages:
        run_pip_install(package, description)
    
    # Testing packages
    testing_packages = [
        ("pytest==7.4.3", "Pytest"),
        ("pytest-asyncio==0.21.1", "Pytest Async"),
    ]
    
    print("\n🧪 Installing testing packages...")
    for package, description in testing_packages:
        run_pip_install(package, description)
    
    # Create directories and files
    print("\n📁 Setting up project structure...")
    create_directories()
    create_env_file()
    
    print("\n✅ Installation completed!")
    print("\n📖 Next steps:")
    print("1. Install Redis for Windows (or use Docker)")
    print("2. Start Redis server")
    print("3. Initialize database: cd src && python database/init.py")
    print("4. Start Celery worker: celery -A src.core.celery_app worker --loglevel=info")
    print("5. Start the server: cd src && python main.py")
    print("6. Visit: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 