"""Global configuration constants for the repository.

DEPRECATED: This file is deprecated. Please use web/backend/config.py instead.
All configuration should be loaded from environment variables via .env file.

For backward compatibility, these values are kept but should be migrated.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Use environment variables with fallback
APP_NAME = os.environ.get('APP_NAME', 'TravelApp')
DEFAULT_API_PREFIX = '/api'
