"""
Settlement Models
Payment/settlement between users
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseModel
from ..constants import SettlementMethod, Currency
from ..config import business_rules


class Settlement(BaseModel):
    """Settlement/payment model"""
    
    settlement_id: Optional[str] = None
    group_id: str = Field(..., min_length=1)
    
    # Payment details
    from_user_id: str = Field(..., min_length=1, description="User who paid")
    to_user_id: str = Field(..., min_length=1, description="User who received payment")
    
    # Denormalized names for display
    from_user_name: Optional[str] = Field(None, max_length=100)
    to_user_name: Optional[str] = Field(None, max_length=100)
    
    # Amount
    amount: Decimal = Field(..., gt=0, description="Settlement amount")
    currency: Currency = Field(default=Currency.USD)
    
    # Payment method
    method: SettlementMethod = Field(default=SettlementMethod.CASH)
    
    # Metadata
    notes: Optional[str] = Field(None, max_length=500)
    proof_url: Optional[str] = Field(None, description="Payment proof/receipt URL")
    settlement_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Created by
    recorded_by: str = Field(..., min_length=1, description="User who recorded settlement")
    
    # Status (settlements are immutable once created)
    is_verified: bool = Field(default=False)
    
    # Soft delete fields
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    @field_validator('amount')
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Ensure amount has correct precision"""
        return round(v, business_rules.BALANCE_PRECISION)
    
    @field_validator('to_user_id')
    @classmethod
    def validate_different_users(cls, v: str, values) -> str:
        """Ensure from_user and to_user are different"""
        if 'from_user_id' in values.data and v == values.data['from_user_id']:
            raise ValueError("Cannot settle with yourself")
        return v


class PaymentProof(BaseModel):
    """Payment proof/receipt"""
    
    settlement_id: str
    uploaded_by: str
    file_url: str
    file_type: str = Field(..., pattern="^(image|pdf)$")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
