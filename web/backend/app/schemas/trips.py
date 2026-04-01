"""Trip-planner validation schemas."""
from app.core.config import Config
from marshmallow import EXCLUDE, Schema, fields, validate


class TripGenerateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    city = fields.String(load_default=None, validate=validate.Length(max=200))
    destination = fields.String(load_default=None, validate=validate.Length(max=200))
    days = fields.Integer(
        load_default=Config.TRIP_DEFAULT_DAYS,
        validate=validate.Range(min=Config.TRIP_MIN_DAYS, max=Config.TRIP_MAX_DAYS),
    )
    pacing = fields.String(
        load_default=Config.TRIP_DEFAULT_PACING,
        validate=validate.OneOf(['R', 'M', 'P', 'r', 'm', 'p']),
    )
    exclude = fields.String(load_default=None)
    require = fields.String(load_default=None)
    places = fields.String(load_default=None)
