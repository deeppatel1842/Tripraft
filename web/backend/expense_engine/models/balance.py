"""
Balance Models
User balances within groups
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from pydantic import Field, field_validator

from .base import BaseModel
from ..constants import Currency
from ..config import business_rules


class Balance(BaseModel):
    """Individual user balance in a group"""
    
    group_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    user_name: Optional[str] = Field(None, max_length=100)
    
    # Balance amount (positive = owed money, negative = owes money)
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: Currency = Field(default=Currency.USD)
    
    # Stats
    total_paid: Decimal = Field(default=Decimal("0.00"), description="Total amount paid")
    total_owed: Decimal = Field(default=Decimal("0.00"), description="Total amount owed")
    
    @field_validator('balance', 'total_paid', 'total_owed')
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Ensure amounts have correct precision"""
        return round(v, business_rules.BALANCE_PRECISION)
    
    def is_settled(self) -> bool:
        """Check if balance is settled (within tolerance)"""
        return abs(self.balance) <= Decimal(str(business_rules.SETTLEMENT_TOLERANCE))
    
    def owes_money(self) -> bool:
        """Check if user owes money"""
        return self.balance < -Decimal(str(business_rules.SETTLEMENT_TOLERANCE))
    
    def is_owed_money(self) -> bool:
        """Check if user is owed money"""
        return self.balance > Decimal(str(business_rules.SETTLEMENT_TOLERANCE))


class GroupBalance(BaseModel):
    """
    Aggregate balance information for a group
    Denormalized for fast reads
    """
    
    group_id: str = Field(..., min_length=1)
    
    # Map of user_id -> balance
    balances: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=0, description="Version for optimistic locking")
    
    def get_balance(self, user_id: str) -> Decimal:
        """Get balance for a specific user"""
        # Access the actual dict value, not the Field descriptor
        balances_data = self.model_dump()['balances']
        return Decimal(str(balances_data.get(user_id, "0.00")))
    
    def set_balance(self, user_id: str, amount: Decimal) -> None:
        """Set balance for a user"""
        # Direct attribute assignment works with Pydantic
        balances_data = dict(self.model_dump()['balances'])
        balances_data[user_id] = float(round(amount, business_rules.BALANCE_PRECISION))
        self.balances = balances_data  # type: ignore
        self.last_updated = datetime.utcnow()
        self.version += 1
    
    def get_all_balances(self) -> list[Balance]:
        """Get all balances as Balance objects"""
        balances_data = self.model_dump()['balances']
        return [
            Balance(
                group_id=self.group_id,
                user_id=user_id,
                balance=Decimal(str(amount))
            )
            for user_id, amount in balances_data.items()
        ]


class BalanceSnapshot(BaseModel):
    """
    Historical snapshot of balances
    Used for audit trail and rollback
    """
    
    snapshot_id: Optional[str] = None
    group_id: str
    
    # Snapshot data
    balances: Dict[str, Decimal]
    
    # Context
    triggered_by: str = Field(..., description="Event that triggered snapshot")
    triggered_by_id: Optional[str] = Field(None, description="ID of expense/settlement")
    
    # Timestamp
    snapshot_at: datetime = Field(default_factory=datetime.utcnow)
