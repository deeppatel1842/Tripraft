"""Group-planner poll validation schemas."""
from marshmallow import (EXCLUDE, Schema, ValidationError, fields, validate,
                         validates)


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
