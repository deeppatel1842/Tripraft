"""
TripRaft Backend -- Main Entry Point
Run this file to start the Flask server.
"""

import logging
import os
import sys
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.core.config import get_config

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    config = get_config()
    app = create_app()

    logger.info(
        "Starting TripRaft Backend | env=%s | http://%s:%s",
        config.FLASK_ENV,
        config.HOST,
        config.PORT,
    )

    try:
        app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    except Exception as exc:
        logger.critical("Failed to start server: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
