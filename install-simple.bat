@echo off
echo 🚀 DeepSeaGuard Simple Installation for Windows
echo ===============================================

echo.
echo 📦 Installing dependencies one by one...

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

REM Core packages
echo Installing FastAPI...
pip install fastapi==0.104.1

echo Installing Uvicorn...
pip install "uvicorn[standard]==0.24.0"

echo Installing other core packages...
pip install python-multipart==0.0.6
pip install python-dotenv==1.0.0

REM Database
echo Installing database packages...
pip install sqlalchemy==2.0.23
pip install aiosqlite==0.19.0

REM Background tasks
echo Installing Celery and Redis...
pip install celery==5.3.4
pip install redis==5.0.1

REM Geo processing (install numpy first)
echo Installing geo processing packages...
pip install numpy==1.25.2
pip install shapely==2.0.2
pip install geojson==3.1.0

REM Validation
echo Installing validation packages...
pip install pydantic==2.5.0
pip install pydantic-settings==2.1.0

REM Async and WebSocket
echo Installing async packages...
pip install httpx==0.25.2
pip install websockets==12.0
pip install aiofiles==23.2.1

REM Caching
echo Installing caching packages...
pip install aioredis==2.0.1

REM Logging
echo Installing logging packages...
pip install structlog==23.2.0

REM Testing
echo Installing testing packages...
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1

echo.
echo 📁 Creating directories...
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "backups" mkdir backups

echo.
echo 📄 Creating .env file...
if not exist ".env" (
    echo # DeepSeaGuard Environment Configuration > .env
    echo. >> .env
    echo # Database (SQLite for development) >> .env
    echo DATABASE_URL=sqlite+aiosqlite:///./deepseaguard.db >> .env
    echo DATABASE_SYNC_URL=sqlite:///./deepseaguard.db >> .env
    echo. >> .env
    echo # Redis >> .env
    echo REDIS_URL=redis://localhost:6379/0 >> .env
    echo CELERY_BROKER_URL=redis://localhost:6379/1 >> .env
    echo CELERY_RESULT_BACKEND=redis://localhost:6379/2 >> .env
    echo. >> .env
    echo # Security >> .env
    echo SECRET_KEY=your-super-secret-key-change-this-in-production >> .env
    echo. >> .env
    echo # Logging >> .env
    echo LOG_LEVEL=INFO >> .env
    echo. >> .env
    echo # Environment >> .env
    echo ENVIRONMENT=development >> .env
    echo DEBUG=true >> .env
)

echo.
echo ✅ Installation completed successfully!
echo.
echo 📖 Next steps:
echo 1. Install Redis for Windows (or use Docker)
echo 2. Start Redis server
echo 3. Initialize database: cd src ^&^& python database/init.py
echo 4. Start Celery worker: celery -A src.core.celery_app worker --loglevel=info
echo 5. Start the server: cd src ^&^& python main.py
echo 6. Visit: http://localhost:8000/docs
echo.
pause 