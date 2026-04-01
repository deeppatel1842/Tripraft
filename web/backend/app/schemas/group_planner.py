"""Group-planner group-level validation schemas."""
from app.core.config import Config
from marshmallow import EXCLUDE, Schema, fields, validate


class CreateTravelGroupSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )
    description = fields.String(
        validate=validate.Length(max=1000),
        load_default=None,
    )
    destination = fields.String(
        validate=validate.Length(max=300),
        load_default=None,
    )
    destination_lat = fields.Float(load_default=None)
    destination_lng = fields.Float(load_default=None)
    destination_type = fields.String(load_default=None)
    destination_id = fields.Raw(load_default=None)
    start_date = fields.String(load_default=None)
    end_date = fields.String(load_default=None)
    estimated_budget = fields.Float(
        validate=validate.Range(min=0, max=Config.MAX_BUDGET_AMOUNT),
        load_default=None,
    )
    budget_currency = fields.String(
        validate=validate.Length(max=10),
        load_default=Config.DEFAULT_CURRENCY,
    )


class UpdateTravelGroupSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(validate=validate.Length(min=1, max=200), load_default=None)
    description = fields.String(validate=validate.Length(max=1000), load_default=None)
    destination = fields.String(validate=validate.Length(max=300), load_default=None)
    start_date = fields.String(load_default=None)
    end_date = fields.String(load_default=None)
    estimated_budget = fields.Float(
        validate=validate.Range(min=0, max=Config.MAX_BUDGET_AMOUNT),
        load_default=None,
    )
    budget_currency = fields.String(validate=validate.Length(max=10), load_default=None)


class UpdateBudgetSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    estimated_budget = fields.Float(
        required=True,
        validate=validate.Range(min=0, max=Config.MAX_BUDGET_AMOUNT),
    )
    budget_currency = fields.String(load_default=None)


class UpdateItineraryDocumentSchema(Schema):
    content = fields.String(load_default=None)
    itinerary_document = fields.String(load_default=None)
