#!/usr/bin/env python3
"""
Startup script for DeepSeaGuard Compliance Engine
Initializes database and starts the server
"""

import subprocess
import sys
import os
import time

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import shapely
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Please run: pip install -r requirements.txt")
        return False

def main():
    """Main startup function"""
    print("🚀 DeepSeaGuard Compliance Engine - Startup")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Change to src directory
    src_dir = os.path.join(os.path.dirname(__file__), 'src')
    if not os.path.exists(src_dir):
        print("❌ src directory not found")
        return
    
    os.chdir(src_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Initialize database
    if not run_command("python database/init.py", "Initializing database"):
        return
    
    # Start server
    print("\n🚀 Starting DeepSeaGuard server...")
    print("   Server will be available at: http://localhost:8000")
    print("   API docs: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start the server
        subprocess.run(["python", "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 