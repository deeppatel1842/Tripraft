# Purpose: Group-planner checklist validation schemas.
"""Group-planner checklist validation schemas."""
from app.core.config import Config
from app.core.schemas.fields import UUIDString
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
    assigned_to_id = UUIDString(load_default=None, allow_none=True)


class UpdateChecklistItemSchema(Schema):
    text = fields.String(validate=validate.Length(min=1, max=500))
    category = fields.String(validate=validate.Length(max=100), allow_none=True)
    priority = fields.String(
        validate=validate.OneOf(Config.PRIORITY_LEVELS),
    )
    due_date = fields.String(allow_none=True)
    assigned_to_id = UUIDString(allow_none=True)
    completed = fields.Boolean()


class AssignChecklistItemSchema(Schema):
    assigned_to_id = UUIDString(required=True, allow_none=True)
