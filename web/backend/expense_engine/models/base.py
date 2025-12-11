"""
Base Model
Common fields and utilities for all Pydantic models
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict, field_validator


# Regex pattern to detect potential injection attempts
INJECTION_PATTERNS = [
    r'<script.*?>',  # XSS script tags
    r'javascript:',  # JavaScript protocol
    r'on\w+\s*=',    # Event handlers
    r'\$\{.*\}',     # Template injection
    r'\{\{.*\}\}',   # Template injection (Angular/Vue style)
]
INJECTION_REGEX = re.compile('|'.join(INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_string(value: str) -> str:
    """
    Sanitize string input to prevent injection attacks
    
    Args:
        value: String to sanitize
        
    Returns:
        Sanitized string
        
    Raises:
        ValueError: If potential injection detected
    """
    if INJECTION_REGEX.search(value):
        raise ValueError("Input contains potentially unsafe content")
    return value.strip()


class BaseModel(PydanticBaseModel):
    """Base model with common fields and configuration"""
    
    # Pydantic v2 configuration
    model_config = ConfigDict(
        # Use enum values instead of enum objects in JSON
        use_enum_values=True,
        # Validate on assignment
        validate_assignment=True,
        # Allow population by field name
        populate_by_name=True,
        # Strict mode for better validation
        strict=False,
        # Custom JSON encoders
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    # Common timestamp fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('*', mode='before')
    @classmethod
    def sanitize_strings(cls, v: Any) -> Any:
        """Sanitize all string inputs"""
        if isinstance(v, str):
            return sanitize_string(v)
        return v
    
    def to_dict(self) -> dict:
        """
        Convert model to dictionary for Firestore
        Handles datetime and Decimal serialization
        """
        data = self.model_dump()
        
        def convert_value(value: Any) -> Any:
            """Recursively convert values for Firestore compatibility"""
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, Decimal):
                # Firestore doesn't support Decimal - convert to float
                return float(value)
            elif isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert_value(item) for item in value]
            return value
        
        return {key: convert_value(val) for key, val in data.items()}
    
    @classmethod
    def from_firestore(cls, doc_dict: dict):
        """
        Create model instance from Firestore document
        Handles datetime parsing
        """
        if not doc_dict:
            return None
        
        # Parse ISO datetime strings back to datetime objects
        for key, value in doc_dict.items():
            if isinstance(value, str) and 'T' in value:
                try:
                    doc_dict[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass  # Not a datetime string
        
        return cls(**doc_dict)
