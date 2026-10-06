# Purpose: Invitation validation schemas.
"""Invitation validation schemas."""
from app.core.schemas.fields import UUIDString
from marshmallow import (Schema, ValidationError, fields, pre_load,
                         validates_schema)


class _EmailNormalizingSchema(Schema):
    """Normalize invitation addresses before duplicate checks and storage."""

    @pre_load
    def normalize_email_fields(self, data, **kwargs):
        normalized = dict(data or {})
        for key in ('email', 'invitee_email', 'invited_email'):
            value = normalized.get(key)
            if isinstance(value, str):
                normalized[key] = value.strip().lower()
        return normalized


class InviteMemberSchema(_EmailNormalizingSchema):
    email = fields.Email(required=True)


class CreateExpenseInvitationSchema(_EmailNormalizingSchema):
    group_id = UUIDString(required=True)
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


class CreateGPInvitationSchema(_EmailNormalizingSchema):
    group_id = UUIDString(required=True)
    email = fields.Email(required=True)
