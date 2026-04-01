"""Settlement validation schemas."""
from app.core.config import Config
from marshmallow import (EXCLUDE, Schema, ValidationError, fields, validate,
                         validates)


class CreateSettlementSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    group_id = fields.Integer(required=True)
    from_user_id = fields.Integer(load_default=None)
    from_user = fields.Integer(load_default=None)      # alias
    to_user_id = fields.Integer(load_default=None)
    to_user = fields.Integer(load_default=None)         # alias
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
