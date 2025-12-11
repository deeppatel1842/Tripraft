"""API routes"""
from .cities import cities_bp
from .countries import countries_bp
from .locations import locations_bp
from .master_locations import master_locations_bp
from .places import places_bp
from .states import states_bp

__all__ = ['countries_bp', 'states_bp', 'cities_bp', 'places_bp', 'locations_bp', 'master_locations_bp']
