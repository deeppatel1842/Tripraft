"""
Places Engine Module

Main entry point for the places discovery and search engine.

Professional layered architecture with dependency injection.
"""

from .app import create_app
from .config import Settings, get_settings

__version__ = '1.0.0'
__all__ = ['create_app', 'Settings', 'get_settings']
