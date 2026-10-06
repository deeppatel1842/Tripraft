# Purpose: Group-planner place validation schemas.
"""Group-planner place validation schemas."""
from app.core.config import Config
from marshmallow import EXCLUDE, Schema, fields, validate


class AddPlaceSchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=300),
    )
    description = fields.String(
        validate=validate.Length(max=1000),
        load_default=None,
    )
    address = fields.String(
        validate=validate.Length(max=500),
        load_default=None,
    )
    latitude = fields.Float(load_default=None)
    longitude = fields.Float(load_default=None)
    category = fields.String(
        validate=validate.OneOf(Config.PLACE_CATEGORIES),
        load_default=Config.DEFAULT_PLACE_CATEGORY,
    )
    visit_date = fields.String(load_default=None)
    suggested_duration = fields.Raw(load_default=None)
    rating = fields.Float(
        validate=validate.Range(min=0, max=5),
        load_default=None,
    )
    photo_url = fields.String(load_default=None)
    website = fields.String(load_default=None)


class UpdatePlaceSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    visit_date = fields.String(load_default=None)
    date = fields.String(load_default=None)
    suggested_duration = fields.Raw(load_default=None)
    duration = fields.Raw(load_default=None)
    suggested_time = fields.String(load_default=None)
    remarks = fields.String(validate=validate.Length(max=2000), load_default=None)
    notes = fields.String(validate=validate.Length(max=2000), load_default=None)
    time = fields.String(load_default=None)


class UpdatePlaceRemarksSchema(Schema):
    remarks = fields.String(validate=validate.Length(max=2000), load_default='')


class GeocodeSchema(Schema):
    place_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=300),
        error_messages={'required': 'Place name is required'},
    )
