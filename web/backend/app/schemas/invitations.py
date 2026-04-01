"""Invitation validation schemas."""
from marshmallow import Schema, ValidationError, fields, validates_schema


class InviteMemberSchema(Schema):
    email = fields.Email(required=True)


class CreateExpenseInvitationSchema(Schema):
    group_id = fields.Integer(required=True)
    invitee_email = fields.Email(load_default=None)
    invited_email = fields.Email(load_default=None)
    email = fields.Email(load_default=None)

    @validates_schema
    def validate_has_email(self, data, **kwargs):
        email = data.get('invitee_email') or data.get('invited_email') or data.get('email')
        if not email:
            raise ValidationError(
                'One of invitee_email, invited_email, or email is required',
                field_name='invitee_email',
            )


class CreateGPInvitationSchema(Schema):
    group_id = fields.Integer(required=True)
    email = fields.Email(required=True)
