"""Group-planner checklist validation schemas."""
from app.core.config import Config
from marshmallow import Schema, fields, validate


class CreateChecklistItemSchema(Schema):
    text = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
    )
    category = fields.String(
        validate=validate.Length(max=100),
        load_default=None,
    )
    priority = fields.String(
        validate=validate.OneOf(Config.PRIORITY_LEVELS),
        load_default=Config.DEFAULT_PRIORITY,
    )
    due_date = fields.String(load_default=None)
    assigned_to_id = fields.Integer(load_default=None)


class UpdateChecklistItemSchema(Schema):
    text = fields.String(validate=validate.Length(min=1, max=500), load_default=None)
    category = fields.String(validate=validate.Length(max=100), load_default=None)
    priority = fields.String(
        validate=validate.OneOf(Config.PRIORITY_LEVELS),
        load_default=None,
    )
    due_date = fields.String(load_default=None)
    assigned_to_id = fields.Integer(load_default=None, allow_none=True)
    completed = fields.Boolean(load_default=None)


class AssignChecklistItemSchema(Schema):
    assigned_to_id = fields.Integer(required=True, allow_none=True)
