# Redis Setup Guide (No Docker)

This guide will help you install Redis for the DeepSeaGuard project without using Docker.

## 🎯 Why Redis is Needed

Redis is required for:
- **Celery message broker** - Background task processing
- **Caching** - Fast data access
- **Session storage** - User sessions
- **Real-time features** - WebSocket support

## 📋 Installation by Operating System

### Windows

#### Option 1: Download from GitHub (Recommended)
1. Go to: https://github.com/microsoftarchive/redis/releases
2. Download the latest `Redis-x64-xxx.msi` file
3. Run the installer
4. Redis will be installed as a Windows service

#### Option 2: Using Chocolatey
```bash
choco install redis-64
```

#### Option 3: Using WSL (Windows Subsystem for Linux)
```bash
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Redis
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis-server

# Enable Redis to start on boot
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server
```

### Linux (CentOS/RHEL/Fedora)

```bash
# Install Redis
sudo dnf install redis  # Fedora
# OR
sudo yum install redis  # CentOS/RHEL

# Start Redis service
sudo systemctl start redis

# Enable Redis to start on boot
sudo systemctl enable redis

# Check status
sudo systemctl status redis
```

### macOS

#### Option 1: Using Homebrew (Recommended)
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Check status
brew services list | grep redis
```

#### Option 2: Manual Installation
```bash
# Download and compile Redis
wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make

# Start Redis server
./src/redis-server
```

## 🔧 Configuration

### Default Redis Configuration
- **Host**: localhost
- **Port**: 6379
- **Password**: None (default)
- **Database**: 0

### Custom Configuration (Optional)
Create a `redis.conf` file:

```conf
# Redis configuration file
port 6379
bind 127.0.0.1
timeout 300
tcp-keepalive 60
loglevel notice
logfile ""
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir ./
```

## 🚀 Starting Redis

### Windows
```bash
# If installed as service
redis-server

# Or start the service
net start redis
```

### Linux/macOS
```bash
# Start Redis server
redis-server

# Or start as service
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS
```

## ✅ Testing Redis Installation

### Test Connection
```bash
# Connect to Redis CLI
redis-cli

# Test ping
127.0.0.1:6379> ping
PONG

# Exit
127.0.0.1:6379> exit
```

### Test from Python
```python
import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Test connection
try:
    r.ping()
    print("✅ Redis connection successful!")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Redis not found
```bash
# Check if Redis is installed
which redis-server
redis-server --version
```

#### 2. Port already in use
```bash
# Check what's using port 6379
netstat -tulpn | grep 6379  # Linux
lsof -i :6379               # macOS
netstat -an | findstr 6379  # Windows
```

#### 3. Permission denied
```bash
# Linux: Check service permissions
sudo systemctl status redis-server

# macOS: Check Homebrew service
brew services list | grep redis
```

#### 4. Connection refused
```bash
# Check if Redis is running
redis-cli ping

# If not running, start it
redis-server
```

### Redis Logs

#### Linux
```bash
# View Redis logs
sudo journalctl -u redis-server

# Follow logs in real-time
sudo journalctl -u redis-server -f
```

#### macOS
```bash
# View Redis logs
tail -f /usr/local/var/log/redis.log
```

#### Windows
```bash
# Check Windows Event Viewer for Redis logs
eventvwr.msc
```

## 🎯 Next Steps

After installing Redis:

1. **Start Redis server**
2. **Run the setup script**: `install-no-docker.bat` (Windows) or `./install-no-docker.sh` (Linux/macOS)
3. **Start the application**: `python start_server.py`
4. **Test the system**: `python test_project.py`

## 📚 Additional Resources

- [Redis Official Documentation](https://redis.io/documentation)
- [Redis Commands Reference](https://redis.io/commands)
- [Redis Configuration](https://redis.io/topics/config) 