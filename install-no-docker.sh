#!/bin/bash

echo "🚀 DeepSeaGuard Setup (No Docker)"
echo "================================="

echo
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "🔧 Creating necessary directories..."
mkdir -p logs uploads backups

echo
echo "📋 Creating .env file..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# DeepSeaGuard Environment Configuration

# Application Settings
APP_NAME=DeepSeaGuard Compliance Engine
APP_VERSION=1.0.0
DEBUG=true
ENVIRONMENT=development

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./deepseaguard.db
DATABASE_SYNC_URL=sqlite:///./deepseaguard.db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security Settings
SECRET_KEY=deepseaguard2024secretkey123456789
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging Configuration
LOG_LEVEL=INFO

# CORS Settings
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS=true

# Other Settings
ENABLE_METRICS=true
CACHE_TTL=300
GEO_CACHE_TTL=3600
MAX_ZONE_SIZE_MB=10
VIOLATION_CHECK_INTERVAL=60
WARNING_THRESHOLD_PERCENT=80.0
WS_HEARTBEAT_INTERVAL=30
WS_MAX_CONNECTIONS=1000
RATE_LIMIT_PER_MINUTE=100
MAX_FILE_SIZE=10485760
UPLOAD_DIR=./uploads
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo
echo "🗄️ Initializing database..."
cd src
python database/init.py
cd ..

echo
echo "✅ Setup complete!"
echo
echo "📋 Next steps:"
echo "1. Install Redis (see REDIS_SETUP.md for instructions)"
echo "2. Start Redis server"
echo "3. Run: python start_server.py"
echo "4. Test with: python test_project.py"
echo
echo "🌐 Access points:"
echo "- Main App: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo 