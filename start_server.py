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
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"❌ Redis is not running: {e}")
        return False

def start_redis():
    """Start Redis server"""
    print("🚀 Starting Redis server...")
    
    # Try to start Redis based on OS
    if os.name == 'nt':  # Windows
        try:
            # Try to start Redis using Windows service
            subprocess.run(['redis-server'], check=True, capture_output=True)
            print("✅ Redis started")
            return True
        except FileNotFoundError:
            print("❌ Redis not found. Please install Redis for Windows:")
            print("   Download from: https://github.com/microsoftarchive/redis/releases")
            return False
    else:  # Linux/Mac
        try:
            subprocess.run(['redis-server'], check=True)
            print("✅ Redis started")
            return True
        except FileNotFoundError:
            print("❌ Redis not found. Please install Redis:")
            print("   Linux: sudo apt-get install redis-server")
            print("   Mac: brew install redis")
            return False

def start_celery_worker():
    """Start Celery worker in background"""
    print("⚙️ Starting Celery worker...")
    
    def run_celery():
        try:
            subprocess.run([
                'celery', '-A', 'src.core.celery_app', 'worker', 
                '--loglevel=info', '--concurrency=2'
            ], cwd=os.getcwd())
        except KeyboardInterrupt:
            print("\n🛑 Celery worker stopped")
    
    celery_thread = threading.Thread(target=run_celery, daemon=True)
    celery_thread.start()
    return celery_thread

def start_celery_beat():
    """Start Celery beat scheduler in background"""
    print("⏰ Starting Celery beat scheduler...")
    
    def run_celery_beat():
        try:
            subprocess.run([
                'celery', '-A', 'src.core.celery_app', 'beat', 
                '--loglevel=info'
            ], cwd=os.getcwd())
        except KeyboardInterrupt:
            print("\n🛑 Celery beat stopped")
    
    beat_thread = threading.Thread(target=run_celery_beat, daemon=True)
    beat_thread.start()
    return beat_thread

def start_fastapi():
    """Start FastAPI server"""
    print("🌐 Starting FastAPI server...")
    
    try:
        subprocess.run([
            'uvicorn', 'src.main:app', 
            '--host', '0.0.0.0', 
            '--port', '8000',
            '--reload'
        ], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n🛑 FastAPI server stopped")

def main():
    """Main startup function"""
    print("🚀 DeepSeaGuard Server Startup (No Docker)")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Check Redis
    if not check_redis():
        print("\n📋 Redis Setup Options:")
        print("1. Install Redis manually (recommended)")
        print("2. Try to start Redis automatically")
        
        choice = input("\nChoose option (1 or 2): ").strip()
        
        if choice == "2":
            if not start_redis():
                print("\n❌ Failed to start Redis. Please install it manually.")
                sys.exit(1)
        else:
            print("\n📋 Please install Redis:")
            print("   Windows: https://github.com/microsoftarchive/redis/releases")
            print("   Linux: sudo apt-get install redis-server")
            print("   Mac: brew install redis")
            sys.exit(1)
    
    # Wait a moment for Redis to be ready
    time.sleep(2)
    
    # Start background services
    print("\n🔄 Starting background services...")
    celery_worker = start_celery_worker()
    celery_beat = start_celery_beat()
    
    # Wait for background services to start
    time.sleep(3)
    
    print("\n✅ All services started!")
    print("\n🌐 Access your application:")
    print("   Main App: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")
    print("   Celery Monitor: http://localhost:5555")
    print("\n📝 Press Ctrl+C to stop all services")
    
    try:
        # Start FastAPI server (this will block)
        start_fastapi()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main() 