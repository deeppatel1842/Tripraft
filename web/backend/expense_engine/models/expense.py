"""
Expense Models
Expense, Split, and ExpenseMetadata
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import Field, field_validator, model_validator

from .base import BaseModel
from ..constants import SplitType, Currency, ExpenseCategory
from ..config import business_rules


class ExpenseSplit(BaseModel):
    """Individual split in an expense"""

    user_id: str = Field(..., min_length=1)
    user_name: Optional[str] = Field(None, max_length=100)  # Denormalized for display

    # Amount for this user
    amount: Decimal = Field(..., gt=0, description="Amount this user owes/paid")

    # For percentage splits
    percentage: Optional[float] = Field(None, ge=0, le=100)

    # For share-based splits
    shares: Optional[int] = Field(None, ge=1)

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Ensure amount has correct precision"""
        return round(v, business_rules.BALANCE_PRECISION)


class Expense(BaseModel):
    """Expense model with validation"""

    expense_id: Optional[str] = None
    group_id: str = Field(..., min_length=1)

    # Basic info
    description: str = Field(
        ..., min_length=1, max_length=business_rules.MAX_DESCRIPTION_LENGTH
    )
    amount: Decimal = Field(
        ...,
        gt=Decimal(str(business_rules.MIN_EXPENSE_AMOUNT)),
        le=Decimal(str(business_rules.MAX_EXPENSE_AMOUNT)),
        description="Total expense amount",
    )
    currency: Currency = Field(default=Currency.USD)

    # Who paid
    paid_by: str = Field(..., min_length=1, description="User ID who paid")
    paid_by_name: Optional[str] = Field(None, max_length=100)  # Denormalized

    # How it's split
    split_type: SplitType = Field(default=SplitType.EQUAL)
    splits: List[ExpenseSplit] = Field(..., min_items=1)

    # Metadata
    created_by: str = Field(..., min_length=1)
    category: Optional[ExpenseCategory] = None
    notes: Optional[str] = Field(None, max_length=1000)
    receipt_url: Optional[str] = None
    expense_date: datetime = Field(default_factory=datetime.utcnow)

    # Status
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Ensure amount has correct precision"""
        return round(v, business_rules.BALANCE_PRECISION)

    @model_validator(mode="after")
    def validate_splits_sum(self):
        """
        Validate that splits sum to total amount
        Tolerance of 0.01 for rounding errors
        """
        if not self.splits:
            raise ValueError("At least one split required")

        # Calculate total from splits
        split_total = sum(split.amount for split in self.splits)

        # Check if splits sum to amount (with tolerance)
        diff = abs(split_total - self.amount)
        if diff > Decimal(str(business_rules.SETTLEMENT_TOLERANCE)):
            raise ValueError(
                f"Splits sum ({split_total}) doesn't match amount ({self.amount}). "
                f"Difference: {diff}"
            )

        # Validate percentage splits
        if self.split_type == SplitType.PERCENTAGE:
            total_percentage = sum(
                split.percentage
                for split in self.splits
                if split.percentage is not None
            )
            if abs(total_percentage - 100.0) > 0.01:
                raise ValueError(
                    f"Percentages must sum to 100%, got {total_percentage}%"
                )

        # Validate payer is in splits
        payer_in_splits = any(split.user_id == self.paid_by for split in self.splits)
        if not payer_in_splits:
            raise ValueError("Payer must be included in splits")

        return self

    def calculate_equal_splits(self, participant_ids: List[str]) -> List[ExpenseSplit]:
        """
        Calculate equal splits for participants
        Used when creating expense with equal split type
        """
        if not participant_ids:
            raise ValueError("At least one participant required")

        amount_per_person = self.amount / Decimal(len(participant_ids))
        amount_per_person = round(amount_per_person, business_rules.BALANCE_PRECISION)

        # Handle rounding - give extra penny to payer
        total_split = amount_per_person * Decimal(len(participant_ids))
        remainder = self.amount - total_split

        splits = []
        for i, user_id in enumerate(participant_ids):
            split_amount = amount_per_person
            # Add remainder to first person (payer)
            if i == 0 and remainder > 0:
                split_amount += remainder

            splits.append(
                ExpenseSplit(
                    user_id=user_id,
                    amount=split_amount,
                    percentage=(
                        100.0 / len(participant_ids)
                        if self.split_type == SplitType.PERCENTAGE
                        else None
                    ),
                )
            )

        return splits


class ExpenseCreate(BaseModel):
    """Model for creating a new expense"""
    
    description: str = Field(
        ..., min_length=1, max_length=business_rules.MAX_DESCRIPTION_LENGTH
    )
    amount: Decimal = Field(
        ...,
        gt=Decimal(str(business_rules.MIN_EXPENSE_AMOUNT)),
        le=Decimal(str(business_rules.MAX_EXPENSE_AMOUNT))
    )
    currency: Currency = Field(default=Currency.USD)
    paid_by: str = Field(..., min_length=1)
    split_type: SplitType = Field(default=SplitType.EQUAL)
    splits: List[ExpenseSplit] = Field(..., min_items=1)
    category: Optional[ExpenseCategory] = None
    notes: Optional[str] = Field(None, max_length=1000)
    receipt_url: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """Model for updating an expense"""
    
    description: Optional[str] = Field(
        None, min_length=1, max_length=business_rules.MAX_DESCRIPTION_LENGTH
    )
    amount: Optional[Decimal] = Field(
        None,
        gt=Decimal(str(business_rules.MIN_EXPENSE_AMOUNT)),
        le=Decimal(str(business_rules.MAX_EXPENSE_AMOUNT))
    )
    currency: Optional[Currency] = None
    splits: Optional[List[ExpenseSplit]] = None
    category: Optional[ExpenseCategory] = None
    notes: Optional[str] = Field(None, max_length=1000)
    receipt_url: Optional[str] = None
