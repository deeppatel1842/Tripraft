"""Expense-group validation schemas."""
from app.core.config import Config
from marshmallow import Schema, fields, validate


class CreateExpenseGroupSchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200, error='Group name must be 1-200 characters'),
    )
    description = fields.String(
        validate=validate.Length(max=1000),
        load_default='',
    )
    currency = fields.String(
        validate=validate.Length(max=10),
        load_default=Config.DEFAULT_CURRENCY,
    )
    category = fields.String(
        validate=validate.Length(max=100),
        load_default=None,
    )


class UpdateExpenseGroupSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=200), load_default=None)
    description = fields.String(validate=validate.Length(max=1000), load_default=None)
    currency = fields.String(validate=validate.Length(max=10), load_default=None)
    category = fields.String(validate=validate.Length(max=100), load_default=None)


class JoinGroupSchema(Schema):
    code = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50),
        error_messages={'required': 'Group code is required'},
    )
