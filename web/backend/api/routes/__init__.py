"""API routes"""
from .countries import countries_bp
from .states import states_bp
from .cities import cities_bp
from .places import places_bp

__all__ = ['countries_bp', 'states_bp', 'cities_bp', 'places_bp']
