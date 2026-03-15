#!/usr/bin/env python
"""
Unified launcher for Proctoring AI System
"""
import argparse
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_banner():
    banner = """
    ╔══════════════════════════════════════════════╗
    ║     Proctoring AI System - Advanced Edition  ║
    ║         Real-time Exam Monitoring            ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)

def main():
    parser = argparse.ArgumentParser(description='Proctoring AI System')
    parser.add_argument('--mode', choices=['gui', 'web', 'test'], 
                       default='gui', help='Run mode')
    parser.add_argument('--port', type=int, default=5000, help='Port for web server')
    parser.add_argument('--headless', action='store_true', help='Run without GUI')
    
    args = parser.parse_args()
    print_banner()
    
    if args.mode == 'gui':
        try:
            from main import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"❌ GUI Error: {e}")
            print("Make sure main.py exists")
            sys.exit(1)
    
    elif args.mode == 'web':
        try:
            from app import run_web_server
            # This call BLOCKS - server runs here
            run_web_server(port=args.port, debug=not args.headless)
            # This line only runs after server stops
            print("✅ Server shutdown complete.")
        except ImportError as e:
            print(f"❌ Web Error: {e}")
            print("Make sure app.py exists and all dependencies are installed")
            print("\nTry installing: pip install flask flask-socketio flask-cors eventlet")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Server stopped by user")
            sys.exit(0)
    
    elif args.mode == 'test':
        import pytest
        sys.exit(pytest.main(['tests/']))

if __name__ == '__main__':
    main()