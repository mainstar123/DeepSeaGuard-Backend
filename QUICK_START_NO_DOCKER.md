# 🚀 DeepSeaGuard Quick Start (No Docker)

This guide will get you up and running with DeepSeaGuard without using Docker.

## 📋 Prerequisites

- **Python 3.8+** installed
- **Redis** installed (see `REDIS_SETUP.md` for installation instructions)
- **Git** (optional, for cloning)

## 🎯 Quick Setup (5 minutes)

### Step 1: Install Dependencies

**Windows:**
```bash
install-no-docker.bat
```

**Linux/Mac:**
```bash
chmod +x install-no-docker.sh
./install-no-docker.sh
```

### Step 2: Install Redis

**Windows:**
1. Download from: https://github.com/microsoftarchive/redis/releases
2. Install the `.msi` file
3. Redis will start automatically

**Linux:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

### Step 3: Start the Application

```bash
python start_server.py
```

### Step 4: Test the System

```bash
python test_project.py
```

## 🌐 Access Your Application

- **🌐 Main App**: http://localhost:8000
- **📚 API Docs**: http://localhost:8000/docs
- **🔍 Celery Monitor**: http://localhost:5555

## 🧪 Testing with Sample Data

The project includes comprehensive sample data for testing:

### Run the Test Script
```bash
python test_project.py
```

This will:
- ✅ Test all API endpoints
- ✅ Generate sample AUV telemetry
- ✅ Create compliance events
- ✅ Test zone management
- ✅ Verify system functionality

### Manual Testing
Visit http://localhost:8000/docs to:
- Test endpoints interactively
- View API documentation
- Send sample requests

## 📊 What's Included

### Sample Data
- **3 ISA Zones** (Jamaica maritime areas)
- **AUV Telemetry** (simulated movement)
- **Compliance Events** (entry/exit/violations)
- **Zone Tracking** (time spent in zones)

### Features Tested
- 🚢 **Telemetry Processing** - AUV position tracking
- 🗺️ **Geo-fencing** - Zone boundary detection
- ⚖️ **Compliance Checking** - Violation detection
- 📊 **Event Logging** - Database storage
- 🔔 **Real-time Alerts** - WebSocket notifications
- ⏰ **Scheduled Tasks** - Background processing

## 🔧 Configuration

### Environment Variables
The setup creates a `.env` file with:
- Database configuration (SQLite)
- Redis connection settings
- Security keys
- Logging levels
- CORS settings

### Customization
Edit `.env` file to:
- Change database settings
- Modify Redis configuration
- Adjust logging levels
- Set custom ports

## 🚨 Troubleshooting

### Common Issues

#### 1. Redis Connection Failed
```bash
# Check if Redis is running
redis-cli ping

# Should return: PONG
```

#### 2. Port Already in Use
```bash
# Check what's using port 8000
netstat -tulpn | grep 8000  # Linux
lsof -i :8000               # macOS
netstat -an | findstr 8000  # Windows
```

#### 3. Python Dependencies Missing
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

#### 4. Database Issues
```bash
# Reinitialize database
cd src
python database/init.py
cd ..
```

### Getting Help

1. **Check logs** in the `logs/` directory
2. **Verify Redis** is running: `redis-cli ping`
3. **Test endpoints** at http://localhost:8000/docs
4. **Run test script**: `python test_project.py`

## 📈 Next Steps

After successful setup:

1. **Explore the API** at http://localhost:8000/docs
2. **Run the test suite**: `python test_project.py`
3. **Add real data sources** (GPS, sensors, etc.)
4. **Customize zones** for your maritime area
5. **Integrate with external systems**

## 🎯 Project Structure

```
deepseaGuard/
├── src/                    # Main application code
│   ├── main.py            # FastAPI application
│   ├── database/          # Database models and setup
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   ├── core/              # Celery configuration
│   └── utils/             # Utilities and sample data
├── logs/                  # Application logs
├── uploads/               # File uploads
├── backups/               # Database backups
├── test_project.py        # Comprehensive test script
├── start_server.py        # Server startup script
├── requirements.txt       # Python dependencies
└── .env                   # Environment configuration
```

## 🚀 Production Deployment

For production, consider:
- **PostgreSQL** instead of SQLite
- **Redis Cluster** for high availability
- **Environment variables** for secrets
- **SSL/TLS** for secure connections
- **Load balancing** for multiple instances

---

**🎉 You're ready to test DeepSeaGuard with sample data!** 