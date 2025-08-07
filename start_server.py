#!/usr/bin/env python3
"""
DeepSeaGuard Server Startup Script (No Docker)
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("[SUCCESS] Redis is running")
        return True
    except Exception as e:
        print(f"[ERROR] Redis is not running: {e}")
        return False

def auto_install_redis():
    """Automatically install and start Redis"""
    print("[INFO] Auto-installing Redis for DeepSeaGuard...")
    
    try:
        # Run the Redis installer script
        result = subprocess.run([
            sys.executable, 'install_redis_windows.py'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("[SUCCESS] Redis auto-installation completed successfully!")
            return True
        else:
            print(f"[ERROR] Redis auto-installation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("[ERROR] Redis installation timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Redis installation error: {e}")
        return False

def start_redis():
    """Start Redis server"""
    print("[INFO] Starting Redis server...")
    
    # Try to start Redis based on OS
    if os.name == 'nt':  # Windows
        try:
            # Try to start Redis using Windows service
            subprocess.run(['redis-server'], check=True, capture_output=True)
            print("[SUCCESS] Redis started")
            return True
        except FileNotFoundError:
            print("[ERROR] Redis not found. Please install Redis for Windows:")
            print("   Download from: https://github.com/microsoftarchive/redis/releases")
            return False
    else:  # Linux/Mac
        try:
            subprocess.run(['redis-server'], check=True)
            print("[SUCCESS] Redis started")
            return True
        except FileNotFoundError:
            print("[ERROR] Redis not found. Please install Redis:")
            print("   Linux: sudo apt-get install redis-server")
            print("   Mac: brew install redis")
            return False

def start_celery_worker():
    """Start Celery worker in background"""
    print("[INFO] Starting Celery worker...")
    
    def run_celery():
        try:
            subprocess.run([
                'celery', '-A', 'src.core.celery_app', 'worker', 
                '--loglevel=info', '--concurrency=2'
            ], cwd=os.getcwd())
        except KeyboardInterrupt:
            print("\n[INFO] Celery worker stopped")
    
    celery_thread = threading.Thread(target=run_celery, daemon=True)
    celery_thread.start()
    return celery_thread

def start_celery_beat():
    """Start Celery beat scheduler in background"""
    print("[INFO] Starting Celery beat scheduler...")
    
    def run_celery_beat():
        try:
            subprocess.run([
                'celery', '-A', 'src.core.celery_app', 'beat', 
                '--loglevel=info'
            ], cwd=os.getcwd())
        except KeyboardInterrupt:
            print("\n[INFO] Celery beat stopped")
    
    beat_thread = threading.Thread(target=run_celery_beat, daemon=True)
    beat_thread.start()
    return beat_thread

def start_fastapi():
    """Start FastAPI server"""
    print("[INFO] Starting FastAPI server...")
    
    try:
        subprocess.run([
            'uvicorn', 'src.main:app', 
            '--host', '0.0.0.0', 
            '--port', '8000',
            '--reload'
        ], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n[INFO] FastAPI server stopped")

def ensure_redis_ready():
    """Ensure Redis is installed and running automatically"""
    print("[INFO] Checking Redis availability...")
    
    # First check if Redis is already running
    if check_redis():
        return True
    
    print("[INFO] Redis not available. Starting automatic installation...")
    
    # Try to auto-install Redis
    if auto_install_redis():
        # Wait for Redis to be ready
        print("[INFO] Waiting for Redis to start...")
        time.sleep(5)
        
        # Test Redis connection
        for attempt in range(3):
            if check_redis():
                print("[SUCCESS] Redis is ready!")
                return True
            else:
                print(f"[INFO] Redis not ready yet, attempt {attempt + 1}/3...")
                time.sleep(3)
        
        print("[ERROR] Redis installation completed but not responding")
        return False
    else:
        print("[ERROR] Failed to auto-install Redis")
        return False

def main():
    """Main startup function"""
    print("[INFO] DeepSeaGuard Server Startup (No Docker)")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("[ERROR] Please run this script from the project root directory")
        sys.exit(1)
    
    # Ensure Redis is ready (auto-install if needed)
    if not ensure_redis_ready():
        print("\n[ERROR] Failed to start Redis. Please check the installation logs.")
        print("[INFO] Manual installation options:")
        print("   Windows: https://github.com/microsoftarchive/redis/releases")
        print("   Linux: sudo apt-get install redis-server")
        print("   Mac: brew install redis")
        sys.exit(1)
    
    # Wait a moment for Redis to be ready
    time.sleep(2)
    
    # Start background services
    print("\n[INFO] Starting background services...")
    celery_worker = start_celery_worker()
    celery_beat = start_celery_beat()
    
    # Wait for background services to start
    time.sleep(3)
    
    print("\n[SUCCESS] All services started!")
    print("\n[INFO] Access your application:")
    print("   Main App: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")
    print("   Celery Monitor: http://localhost:5555")
    print("\n[INFO] Press Ctrl+C to stop all services")
    
    try:
        # Start FastAPI server (this will block)
        start_fastapi()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main() 