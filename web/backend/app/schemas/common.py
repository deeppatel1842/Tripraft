"""
Input Validation Schemas — shared_db/schemas.py

Marshmallow schemas for request payload validation.
Used by routes to validate and sanitize user input
before it reaches the service layer.
"""
from marshmallow import (EXCLUDE, Schema, ValidationError, fields, validate,
                         validates)

# ============================================================================
# AUTH SCHEMAS
# ============================================================================

class SignupSchema(Schema):
    email = fields.Email(required=True, error_messages={'required': 'Email is required'})
    password = fields.String(
        required=True,
        validate=validate.Length(min=8, max=128, error='Password must be 8-128 characters'),
    )
    display_name = fields.String(
        validate=validate.Length(min=1, max=100),
        load_default=None,
    )

    @validates('password')
    def validate_password_strength(self, value, **kwargs):
        if value.isdigit():
            raise ValidationError('Password cannot be all digits')
        if value.isalpha():
            raise ValidationError('Password must contain at least one number')


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1))


class ChangePasswordSchema(Schema):
    current_password = fields.String(required=True)
    new_password = fields.String(
        required=True,
        validate=validate.Length(min=8, max=128),
    )


class CheckEmailSchema(Schema):
    email = fields.Email(required=True)


# ============================================================================
# EXPENSE SCHEMAS
# ============================================================================

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
        load_default='INR',
    )
    category = fields.String(
        validate=validate.Length(max=100),
        load_default=None,
    )


class CreateExpenseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
    )
    amount = fields.Float(
        required=True,
        validate=validate.Range(min=0.01, max=1_000_000),
    )
    group_id = fields.Integer(load_default=None, allow_none=True)
    paid_by = fields.Raw(load_default=None, allow_none=True)
    split_type = fields.String(
        validate=validate.OneOf(['equal', 'exact', 'percentage', 'shares',
                                  'EQUAL', 'EXACT', 'PERCENTAGE', 'SHARES',
                                  'none']),
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
    currency = fields.String(validate=validate.Length(max=10), load_default='USD')


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
        validate=validate.Range(min=0.01, max=1_000_000),
    )
    method = fields.String(
        validate=validate.OneOf(['cash', 'bank_transfer', 'upi', 'paypal', 'other']),
        load_default='cash',
    )
    notes = fields.String(validate=validate.Length(max=1000), load_default=None)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Ensure amount is positive."""
        if value <= 0:
            raise ValidationError('Amount must be greater than zero')


# ============================================================================
# GROUP PLANNER SCHEMAS
# ============================================================================

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
        validate=validate.Range(min=0, max=100_000_000),
        load_default=None,
    )
    budget_currency = fields.String(
        validate=validate.Length(max=10),
        load_default='USD',
    )


class UpdateBudgetSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    estimated_budget = fields.Float(
        required=True,
        validate=validate.Range(min=0, max=100_000_000),
    )
    budget_currency = fields.String(load_default=None)


class InviteMemberSchema(Schema):
    email = fields.Email(required=True)


class CreatePollSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None)
    question = fields.String(load_default=None)               # alias for name
    options = fields.List(
        fields.String(validate=validate.Length(min=1, max=200)),
        required=True,
        validate=validate.Length(min=2, max=10),
    )
    is_multiple_choice = fields.Boolean(load_default=False)
    expires_at = fields.String(load_default=None)

    @validates('options')
    def validate_options(self, value, **kwargs):
        """Ensure no duplicate options."""
        if len(value) != len(set(value)):
            raise ValidationError('Options must be unique')


class VotePollSchema(Schema):
    option = fields.String(load_default=None)
    option_index = fields.Integer(
        validate=validate.Range(min=0),
        load_default=None,
    )


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
        validate=validate.OneOf(['low', 'medium', 'high']),
        load_default='medium',
    )
    due_date = fields.String(load_default=None)
    assigned_to_id = fields.Integer(load_default=None)


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
        validate=validate.OneOf(['attraction', 'restaurant', 'hotel', 'event', 'other']),
        load_default='attraction',
    )
    visit_date = fields.String(load_default=None)
    suggested_duration = fields.Raw(load_default=None)
    rating = fields.Float(
        validate=validate.Range(min=0, max=5),
        load_default=None,
    )
    photo_url = fields.String(load_default=None)
    website = fields.String(load_default=None)


# ============================================================================
# HELPER: Validate request data
# ============================================================================

def validate_request(schema_class, data):
    """
    Validate request data against a marshmallow schema.

    Args:
        schema_class: A marshmallow Schema class (not an instance).
        data: The raw dict to validate.

    Returns:
        (validated_data, None) on success.
        (None, error_dict) on failure.
    """
    schema = schema_class()
    try:
        result = schema.load(data)
        return result, None
    except ValidationError as err:
        return None, err.messages
