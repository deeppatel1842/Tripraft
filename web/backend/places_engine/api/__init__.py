"""
Places Engine API Module

Flask blueprints for places-related endpoints.
"""

from .routes import places_bp, init_service
from .admin import admin_bp

__all__ = ['places_bp', 'admin_bp', 'init_service']
