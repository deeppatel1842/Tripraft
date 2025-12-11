"""
Firestore Serialization Utilities

Provides helper functions for converting Python types to Firestore-compatible values.
Firestore doesn't support Decimal natively, so we need to convert them to floats.

Phase 20: Added for snapshot updates with balance data
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Any, Dict, List, Union


def to_firestore_value(value: Any) -> Any:
    """
    Convert a Python value to a Firestore-compatible value.
    
    Handles:
    - Decimal -> float
    - datetime/date -> ISO string
    - dict -> recursively converted dict
    - list -> recursively converted list
    
    Args:
        value: Any Python value
        
    Returns:
        Firestore-compatible value
    """
    if value is None:
        return None
    
    if isinstance(value, Decimal):
        return float(value)
    
    if isinstance(value, datetime):
        return value.isoformat()
    
    if isinstance(value, date):
        return value.isoformat()
    
    if isinstance(value, dict):
        return {k: to_firestore_value(v) for k, v in value.items()}
    
    if isinstance(value, (list, tuple)):
        return [to_firestore_value(item) for item in value]
    
    # Basic types (str, int, float, bool) pass through
    return value


def serialize_balances(balances: Dict[str, Union[Decimal, float]]) -> Dict[str, float]:
    """
    Convert a balance dictionary with Decimal values to float values.
    
    Args:
        balances: Dict mapping user IDs to balance amounts (possibly Decimal)
        
    Returns:
        Dict mapping user IDs to float balance amounts
    """
    if not balances:
        return {}
    
    return {
        user_id: float(amount) if isinstance(amount, Decimal) else amount
        for user_id, amount in balances.items()
    }


def serialize_expense_for_snapshot(expense: Dict) -> Dict:
    """
    Serialize an expense dict for storage in a snapshot's recentExpenses list.
    
    Args:
        expense: Expense dictionary from database
        
    Returns:
        Serialized expense dict safe for Firestore
    """
    return {
        'id': expense.get('expense_id') or expense.get('id'),
        'description': expense.get('description', ''),
        'amount': float(expense.get('amount', 0)) if isinstance(expense.get('amount'), Decimal) else expense.get('amount', 0),
        'currency': expense.get('currency', 'USD'),
        'paidBy': expense.get('paid_by', ''),
        'paidByName': expense.get('paid_by_name', ''),
        'category': expense.get('category', ''),
        'date': expense.get('expense_date') or expense.get('date'),
        'createdAt': expense.get('created_at'),
        'splitType': expense.get('split_type', 'EQUAL')
    }


def serialize_document(data: Dict) -> Dict:
    """
    Recursively serialize a document dictionary for Firestore.
    
    Args:
        data: Document dictionary
        
    Returns:
        Serialized dictionary safe for Firestore
    """
    return to_firestore_value(data)
