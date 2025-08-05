@echo off
echo 🚀 DeepSeaGuard Setup (No Docker)
echo =================================

echo.
echo 📦 Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo 🔧 Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "backups" mkdir backups

echo.
echo 📋 Creating .env file...
if not exist ".env" (
    echo # DeepSeaGuard Environment Configuration > .env
    echo. >> .env
    echo # Application Settings >> .env
    echo APP_NAME=DeepSeaGuard Compliance Engine >> .env
    echo APP_VERSION=1.0.0 >> .env
    echo DEBUG=true >> .env
    echo ENVIRONMENT=development >> .env
    echo. >> .env
    echo # Server Configuration >> .env
    echo HOST=0.0.0.0 >> .env
    echo PORT=8000 >> .env
    echo WORKERS=1 >> .env
    echo. >> .env
    echo # Database Configuration >> .env
    echo DATABASE_URL=sqlite+aiosqlite:///./deepseaguard.db >> .env
    echo DATABASE_SYNC_URL=sqlite:///./deepseaguard.db >> .env
    echo. >> .env
    echo # Redis Configuration >> .env
    echo REDIS_URL=redis://localhost:6379/0 >> .env
    echo REDIS_HOST=localhost >> .env
    echo REDIS_PORT=6379 >> .env
    echo REDIS_DB=0 >> .env
    echo REDIS_PASSWORD= >> .env
    echo. >> .env
    echo # Celery Configuration >> .env
    echo CELERY_BROKER_URL=redis://localhost:6379/1 >> .env
    echo CELERY_RESULT_BACKEND=redis://localhost:6379/2 >> .env
    echo. >> .env
    echo # Security Settings >> .env
    echo SECRET_KEY=deepseaguard2024secretkey123456789 >> .env
    echo ALGORITHM=HS256 >> .env
    echo ACCESS_TOKEN_EXPIRE_MINUTES=30 >> .env
    echo. >> .env
    echo # Logging Configuration >> .env
    echo LOG_LEVEL=INFO >> .env
    echo. >> .env
    echo # CORS Settings >> .env
    echo CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"] >> .env
    echo CORS_ALLOW_CREDENTIALS=true >> .env
    echo. >> .env
    echo # Other Settings >> .env
    echo ENABLE_METRICS=true >> .env
    echo CACHE_TTL=300 >> .env
    echo GEO_CACHE_TTL=3600 >> .env
    echo MAX_ZONE_SIZE_MB=10 >> .env
    echo VIOLATION_CHECK_INTERVAL=60 >> .env
    echo WARNING_THRESHOLD_PERCENT=80.0 >> .env
    echo WS_HEARTBEAT_INTERVAL=30 >> .env
    echo WS_MAX_CONNECTIONS=1000 >> .env
    echo RATE_LIMIT_PER_MINUTE=100 >> .env
    echo MAX_FILE_SIZE=10485760 >> .env
    echo UPLOAD_DIR=./uploads >> .env
    echo ✅ .env file created
) else (
    echo ✅ .env file already exists
)

echo.
echo 🗄️ Initializing database...
cd src
python database/init.py
cd ..

echo.
echo ✅ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Install Redis (see instructions below)
echo 2. Start Redis server
echo 3. Run: python start_server.py
echo 4. Test with: python test_project.py
echo.
echo 🌐 Access points:
echo - Main App: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo.
pause 