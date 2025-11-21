"""
TripRaft Backend - Main Entry Point
Run this file to start the Flask server.
"""
import sys
import os
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    # Set UTF-8 encoding for stdout
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    # Set Python to use UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api import create_app
from api.config import get_config

def main():
    """Main entry point"""
    config = get_config()
    app = create_app()
    
    print("\n" + "="*60)
    print("START TripRaft Backend Server")
    print("="*60)
    print(f"Environment: {config.FLASK_ENV}")
    print(f"Server: http://{config.HOST}:{config.PORT}")
    print(f"Health Check: http://{config.HOST}:{config.PORT}/health")
    print("="*60 + "\n")
    
    try:
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
    except Exception as e:
        print(f"\nFAILED to start server: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
