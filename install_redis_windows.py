#!/usr/bin/env python3
"""
Redis Auto-Installation Script for Windows
Automatically downloads, installs, and starts Redis for DeepSeaGuard
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import tempfile
import shutil
import time
import threading
from pathlib import Path

class RedisInstaller:
    def __init__(self):
        self.redis_url = "https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip"
        self.redis_dir = Path.home() / "redis"
        self.redis_exe = self.redis_dir / "redis-server.exe"
        self.redis_cli = self.redis_dir / "redis-cli.exe"
        self.redis_process = None
        
    def print_status(self, message, status="INFO"):
        """Print status message with color coding"""
        colors = {
            "INFO": "\033[94m",    # Blue
            "SUCCESS": "\033[92m", # Green
            "WARNING": "\033[93m", # Yellow
            "ERROR": "\033[91m",   # Red
            "RESET": "\033[0m"     # Reset
        }
        print(f"{colors.get(status, '')}[{status}] {message}{colors['RESET']}")
        
    def check_redis_installed(self):
        """Check if Redis is already installed"""
        if self.redis_exe.exists():
            self.print_status(f"Redis found at: {self.redis_exe}", "SUCCESS")
            return True
        return False
        
    def download_redis(self):
        """Download Redis for Windows"""
        self.print_status("Downloading Redis for Windows...", "INFO")
        
        try:
            # Create temp directory
            temp_dir = Path(tempfile.gettempdir()) / "redis_download"
            temp_dir.mkdir(exist_ok=True)
            
            # Download Redis
            zip_path = temp_dir / "redis.zip"
            self.print_status(f"Downloading from: {self.redis_url}", "INFO")
            
            urllib.request.urlretrieve(self.redis_url, zip_path)
            self.print_status("Download completed", "SUCCESS")
            
            return zip_path
            
        except Exception as e:
            self.print_status(f"Download failed: {str(e)}", "ERROR")
            return None
            
    def install_redis(self, zip_path):
        """Install Redis from downloaded zip"""
        self.print_status("Installing Redis...", "INFO")
        
        try:
            # Create Redis directory
            self.redis_dir.mkdir(exist_ok=True)
            
            # Extract Redis
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.redis_dir)
            
            # Clean up downloaded file
            zip_path.unlink()
            
            self.print_status(f"Redis installed to: {self.redis_dir}", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_status(f"Installation failed: {str(e)}", "ERROR")
            return False
            
    def start_redis_server(self):
        """Start Redis server in background"""
        self.print_status("Starting Redis server...", "INFO")
        
        try:
            # Start Redis server in background
            self.redis_process = subprocess.Popen(
                [str(self.redis_exe), "--daemonize", "yes"],
                cwd=self.redis_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a moment for Redis to start
            time.sleep(2)
            
            # Test Redis connection
            if self.test_redis_connection():
                self.print_status("Redis server started successfully", "SUCCESS")
                return True
            else:
                self.print_status("Redis server failed to start", "ERROR")
                return False
                
        except Exception as e:
            self.print_status(f"Failed to start Redis: {str(e)}", "ERROR")
            return False
            
    def test_redis_connection(self):
        """Test Redis connection"""
        try:
            result = subprocess.run(
                [str(self.redis_cli), "ping"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "PONG" in result.stdout
        except:
            return False
            
    def create_redis_config(self):
        """Create Redis configuration file"""
        config_content = """# Redis configuration for DeepSeaGuard
port 6379
bind 127.0.0.1
timeout 300
tcp-keepalive 60
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir ./
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
lua-time-limit 5000
slowlog-log-slower-than 10000
slowlog-max-len 128
notify-keyspace-events ""
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit slave 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
hz 10
aof-rewrite-incremental-fsync yes
"""
        
        config_path = self.redis_dir / "redis.conf"
        with open(config_path, 'w') as f:
            f.write(config_content)
            
        self.print_status(f"Redis config created: {config_path}", "SUCCESS")
        
    def install_and_start(self):
        """Main installation and startup process"""
        self.print_status("DeepSeaGuard Redis Auto-Installer", "INFO")
        self.print_status("=" * 50, "INFO")
        
        # Check if Redis is already installed
        if self.check_redis_installed():
            self.print_status("Redis is already installed", "SUCCESS")
        else:
            # Download and install Redis
            zip_path = self.download_redis()
            if not zip_path:
                return False
                
            if not self.install_redis(zip_path):
                return False
                
            # Create configuration
            self.create_redis_config()
        
        # Start Redis server
        if not self.start_redis_server():
            return False
            
        # Final test
        if self.test_redis_connection():
            self.print_status("Redis is ready for DeepSeaGuard!", "SUCCESS")
            self.print_status(f"Redis CLI: {self.redis_cli}", "INFO")
            self.print_status(f"Redis Server: {self.redis_exe}", "INFO")
            return True
        else:
            self.print_status("Redis installation completed but connection test failed", "WARNING")
            return False

def main():
    """Main function"""
    installer = RedisInstaller()
    
    try:
        success = installer.install_and_start()
        if success:
            print("\n" + "=" * 50)
            print("[SUCCESS] Redis installation completed successfully!")
            print("[INFO] You can now run: python start_server.py")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("[ERROR] Redis installation failed!")
            print("Please try manual installation:")
            print("1. Download Redis from: https://github.com/microsoftarchive/redis/releases")
            print("2. Install and start Redis manually")
            print("=" * 50)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[ERROR] Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 