# Purpose: Expense-related validation schemas.
"""Expense-related validation schemas."""
from decimal import Decimal, ROUND_HALF_UP

from app.core.config import Config
from app.core.schemas.fields import UUIDString
from marshmallow import EXCLUDE, Schema, fields, validate


class CreateExpenseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
    )
    amount = fields.Decimal(
        required=True,
        places=2,
        rounding=ROUND_HALF_UP,
        as_string=False,
        validate=validate.Range(
            min=Decimal('0.01'),
            max=Decimal(str(Config.MAX_EXPENSE_AMOUNT)),
        ),
    )
    group_id = UUIDString(load_default=None, allow_none=True)
    paid_by = UUIDString(load_default=None, allow_none=True)
    split_type = fields.String(
        validate=validate.OneOf(Config.SPLIT_TYPES + [s.upper() for s in Config.SPLIT_TYPES]),
        load_default='equal',
    )
    splits = fields.List(fields.Dict(), load_default=None, allow_none=True)
    category = fields.String(
        validate=validate.Length(max=100),
        load_default=None,
        allow_none=True,
    )
    expense_date = fields.String(load_default=None, allow_none=True)
    date = fields.String(load_default=None, allow_none=True)
    notes = fields.String(validate=validate.Length(max=1000), load_default=None, allow_none=True)
    receipt_url = fields.String(load_default=None, allow_none=True)
    currency = fields.String(validate=validate.Length(max=10), load_default=Config.DEFAULT_CURRENCY)


class UpdateExpenseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    description = fields.String(validate=validate.Length(min=1, max=500), load_default=None)
    amount = fields.Decimal(
        places=2,
        rounding=ROUND_HALF_UP,
        as_string=False,
        validate=validate.Range(
            min=Decimal('0.01'),
            max=Decimal(str(Config.MAX_EXPENSE_AMOUNT)),
        ),
        load_default=None,
    )
    paid_by = UUIDString(load_default=None, allow_none=True)
    split_type = fields.String(
        validate=validate.OneOf(Config.SPLIT_TYPES + [s.upper() for s in Config.SPLIT_TYPES]),
        load_default=None,
    )
    splits = fields.List(fields.Dict(), load_default=None, allow_none=True)
    category = fields.String(validate=validate.Length(max=100), load_default=None, allow_none=True)
    expense_date = fields.String(load_default=None, allow_none=True)
    notes = fields.String(validate=validate.Length(max=1000), load_default=None, allow_none=True)
