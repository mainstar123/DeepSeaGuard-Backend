#!/usr/bin/env python3
"""
DeepSeaGuard Simple Startup Script (No Redis Required)
"""

import os
import sys
import subprocess
from pathlib import Path

def start_fastapi():
    """Start FastAPI server without Redis dependency"""
    print("🌐 Starting FastAPI server (Simple Mode)...")
    print("📝 Note: Some features requiring Redis will be disabled")
    
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
    print("🚀 DeepSeaGuard Simple Startup (No Redis)")
    print("=" * 45)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    print("\n✅ Starting server in simple mode...")
    print("🌐 Access your application:")
    print("   Main App: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs")
    print("\n📝 Press Ctrl+C to stop the server")
    
    try:
        # Start FastAPI server (this will block)
        start_fastapi()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main() 