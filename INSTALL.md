# DeepSeaGuard Installation Guide

## 🚀 Quick Installation Options

### Option 1: Simple Batch File (Windows)
```bash
install-simple.bat
```

### Option 2: Python Script (All Platforms)
```bash
python install-python.py
```

### Option 3: Manual Installation (Recommended for troubleshooting)

#### Step 1: Upgrade pip
```bash
python -m pip install --upgrade pip
```

#### Step 2: Install core packages one by one
```bash
# Core FastAPI
pip install fastapi==0.104.1
pip install "uvicorn[standard]==0.24.0"
pip install python-multipart==0.0.6
pip install python-dotenv==1.0.0

# Database
pip install sqlalchemy==2.0.23
pip install aiosqlite==0.19.0

# Background tasks
pip install celery==5.3.4
pip install redis==5.0.1

# Geo processing (install numpy first)
pip install numpy==1.25.2
pip install shapely==2.0.2
pip install geojson==3.1.0

# Validation
pip install pydantic==2.5.0
pip install pydantic-settings==2.1.0

# Async and WebSocket
pip install httpx==0.25.2
pip install websockets==12.0
pip install aiofiles==23.2.1

# Caching
pip install aioredis==2.0.1

# Logging
pip install structlog==23.2.0

# Testing
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
```

#### Step 3: Create directories
```bash
mkdir logs
mkdir uploads
mkdir backups
```

#### Step 4: Create .env file
Create a `.env` file with the following content:
```env
# DeepSeaGuard Environment Configuration

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
```

## 🔧 Troubleshooting

### Common Issues

#### 1. "Cannot import 'setuptools.build_meta'" Error
**Solution**: Install packages individually instead of using requirements files.

#### 2. Shapely Installation Fails
**Solution**: Install numpy first, then shapely:
```bash
pip install numpy==1.25.2
pip install shapely==2.0.2
```

#### 3. Celery Installation Issues
**Solution**: Install with specific version:
```bash
pip install celery==5.3.4
```

#### 4. Redis Connection Issues
**Solution**: Install Redis for Windows or use Docker:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine
```

### Alternative Installation Methods

#### Using Conda (if available)
```bash
conda install -c conda-forge fastapi uvicorn sqlalchemy shapely pandas numpy
pip install celery redis aiosqlite python-dotenv
```

#### Using Poetry (if available)
```bash
poetry install
```

## 📋 System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, Linux, macOS
- **Memory**: 2GB RAM minimum
- **Storage**: 1GB free space

## 🎯 Next Steps After Installation

1. **Install Redis**:
   - Windows: Download from https://redis.io/download
   - Linux: `sudo apt-get install redis-server`
   - macOS: `brew install redis`

2. **Start Redis**:
   ```bash
   redis-server
   ```

3. **Initialize Database**:
   ```bash
   cd src
   python database/init.py
   ```

4. **Start Celery Worker**:
   ```bash
   celery -A src.core.celery_app worker --loglevel=info
   ```

5. **Start the Server**:
   ```bash
   cd src
   python main.py
   ```

6. **Access the API**:
   - Swagger UI: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## 🧪 Testing the Installation

Run the test script to verify everything is working:
```bash
python test_system.py
```

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Try the manual installation method
3. Ensure you have Python 3.8+ installed
4. Make sure Redis is running 