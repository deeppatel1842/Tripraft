"""
TripRaft Backend API
Professional Flask application for expense management and group planning.
"""

__version__ = '1.0.0'
__author__ = 'TripRaft Team'

from .app import create_app
from .config import get_config

__all__ = ['create_app', 'get_config']
