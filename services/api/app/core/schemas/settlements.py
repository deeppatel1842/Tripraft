# Purpose: Settlement validation schemas.
"""Settlement validation schemas."""
from app.core.config import Config
from app.core.schemas.fields import UUIDString
from marshmallow import (EXCLUDE, Schema, ValidationError, fields, validate,
                         validates)


class CreateSettlementSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    group_id = UUIDString(required=True)
    from_user_id = UUIDString(load_default=None, allow_none=True)
    from_user = UUIDString(load_default=None, allow_none=True)      # alias
    to_user_id = UUIDString(load_default=None, allow_none=True)
    to_user = UUIDString(load_default=None, allow_none=True)         # alias
    amount = fields.Float(
        required=True,
        validate=validate.Range(min=0.01, max=Config.MAX_EXPENSE_AMOUNT),
    )
    method = fields.String(
        validate=validate.OneOf(Config.PAYMENT_METHODS),
        load_default=Config.DEFAULT_PAYMENT_METHOD,
    )
    notes = fields.String(validate=validate.Length(max=1000), load_default=None)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Ensure amount is positive."""
        if value <= 0:
            raise ValidationError('Amount must be greater than zero')
