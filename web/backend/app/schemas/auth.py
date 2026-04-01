"""Auth-related validation schemas."""
from app.core.config import Config
from marshmallow import Schema, ValidationError, fields, validate, validates


class SignupSchema(Schema):
    email = fields.Email(required=True, error_messages={'required': 'Email is required'})
    password = fields.String(
        required=True,
        validate=validate.Length(min=Config.PASSWORD_MIN_LENGTH, max=Config.PASSWORD_MAX_LENGTH, error=f'Password must be {Config.PASSWORD_MIN_LENGTH}-{Config.PASSWORD_MAX_LENGTH} characters'),
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
        validate=validate.Length(min=Config.PASSWORD_MIN_LENGTH, max=Config.PASSWORD_MAX_LENGTH),
    )


class CheckEmailSchema(Schema):
    email = fields.Email(required=True)


class UpdateProfileSchema(Schema):
    display_name = fields.String(validate=validate.Length(max=100), load_default=None)
    phone = fields.String(validate=validate.Length(max=20), load_default=None)
    photo_url = fields.String(validate=validate.Length(max=500), load_default=None)
    default_currency = fields.String(validate=validate.Length(max=10), load_default=None)
