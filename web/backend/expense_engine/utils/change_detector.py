"""
Change Detection Utilities for Smart Cache Invalidation

This module provides functions to detect whether expense updates require
balance recalculation or are metadata-only changes.

Phase 3 Optimization: Skip expensive balance recalculations for metadata-only edits.
"""

def is_metadata_only_change(old_expense, new_data):
    """
    Detect if expense update only changes metadata (no balance recalculation needed).
    
    This is the inverse of is_financial_change() - optimized for Phase 3.
    
    Args:
        old_expense (dict): Original expense data from database
        new_data (dict): Updated expense data from request
    
    Returns:
        bool: True if only metadata changed (skip recalc), False if financial data changed
        
    Examples:
        Metadata-only (True - skip recalc):
        - Description: "dinner" → "lunch"
        - Category: "Food" → "Entertainment"
        - Date: "2025-11-06" → "2025-11-05"
        
        Financial changes (False - need recalc):
        - Amount: $100 → $150
        - Paid by: User A → User B
        - Splits: [$50, $50] → [$75, $25]
    """
    # If any financial field changed, it's NOT metadata-only
    return not is_financial_change(old_expense, new_data)


def is_financial_change(old_expense, new_data):
    """
    Detect if expense update changes financial data requiring balance recalculation.
    
    Args:
        old_expense (dict): Original expense data from database
        new_data (dict): Updated expense data from request
    
    Returns:
        bool: True if balance recalculation needed, False if metadata-only change
        
    Examples:
        Metadata-only (False):
        - Description: "dinner" → "lunch"
        - Category: "Food" → "Entertainment"
        - Date: "2025-11-06" → "2025-11-05"
        
        Financial changes (True):
        - Amount: $100 → $150
        - Paid by: User A → User B
        - Splits: [$50, $50] → [$75, $25]
    """
    if not old_expense or not new_data:
        # Safety: If we can't compare, assume recalc needed
        return True
    
    # Financial fields that affect balances
    financial_fields = {
        'amount': _compare_amounts,
        'paid_by': _compare_simple,
        'splits': _compare_splits
    }
    
    for field, comparator in financial_fields.items():
        # Check if field exists in update data (only compare if being updated)
        if field in new_data:
            old_value = old_expense.get(field)
            new_value = new_data.get(field)
            
            # Use appropriate comparator for this field type
            if not comparator(old_value, new_value):
                return True  # Values differ, recalc needed
    
    # All financial fields either unchanged or not being updated
    return False


def _compare_amounts(old_amount, new_amount):
    """Compare expense amounts, handling float precision."""
    if old_amount is None or new_amount is None:
        return old_amount == new_amount
    
    # Convert to float for comparison (handle string inputs)
    try:
        old_float = float(old_amount)
        new_float = float(new_amount)
        # Use small epsilon for float comparison
        return abs(old_float - new_float) < 0.001
    except (ValueError, TypeError):
        return old_amount == new_amount


def _compare_simple(old_value, new_value):
    """Direct equality comparison for simple fields like paid_by."""
    return old_value == new_value


def _compare_splits(old_splits, new_splits):
    """
    Compare split arrays for financial equivalence.
    
    Splits are considered equal if they have the same users with same amounts,
    regardless of order.
    """
    if old_splits is None or new_splits is None:
        return old_splits == new_splits
    
    if not isinstance(old_splits, list) or not isinstance(new_splits, list):
        return old_splits == new_splits
    
    if len(old_splits) != len(new_splits):
        return False
    
    # Sort splits by user_id for consistent comparison
    try:
        old_sorted = sorted(old_splits, key=lambda x: x.get('user_id', ''))
        new_sorted = sorted(new_splits, key=lambda x: x.get('user_id', ''))
    except (KeyError, TypeError, AttributeError):
        # If sorting fails, fall back to direct comparison
        return old_splits == new_splits
    
    # Compare each split
    for old_split, new_split in zip(old_sorted, new_sorted):
        # User ID must match
        if old_split.get('user_id') != new_split.get('user_id'):
            return False
        
        # Amount must match (within float precision)
        old_amt = old_split.get('amount', 0)
        new_amt = new_split.get('amount', 0)
        if not _compare_amounts(old_amt, new_amt):
            return False
    
    return True


def get_changed_fields(old_expense, new_data):
    """
    Get list of field names that changed in the update.
    
    Useful for logging and debugging.
    
    Args:
        old_expense (dict): Original expense data
        new_data (dict): Updated expense data
        
    Returns:
        list: Names of fields that changed
    """
    if not old_expense or not new_data:
        return []
    
    changed = []
    
    for field, new_value in new_data.items():
        old_value = old_expense.get(field)
        
        # Use appropriate comparison based on field type
        if field == 'amount':
            if not _compare_amounts(old_value, new_value):
                changed.append(field)
        elif field == 'splits':
            if not _compare_splits(old_value, new_value):
                changed.append(field)
        else:
            if old_value != new_value:
                changed.append(field)
    
    return changed


def format_change_summary(old_expense, new_data):
    """
    Create human-readable summary of changes for logging.
    
    Args:
        old_expense (dict): Original expense data
        new_data (dict): Updated expense data
        
    Returns:
        str: Formatted summary like "description: dinner→lunch, amount: $100→$150"
    """
    if not old_expense or not new_data:
        return "No comparison data"
    
    changes = []
    
    for field in get_changed_fields(old_expense, new_data):
        old_value = old_expense.get(field)
        new_value = new_data.get(field)
        
        # Format based on field type
        if field == 'amount':
            changes.append(f"{field}: ${old_value}→${new_value}")
        elif field == 'splits':
            old_count = len(old_value) if isinstance(old_value, list) else 0
            new_count = len(new_value) if isinstance(new_value, list) else 0
            changes.append(f"{field}: {old_count} users→{new_count} users")
        else:
            # Truncate long values
            old_str = str(old_value)[:30]
            new_str = str(new_value)[:30]
            changes.append(f"{field}: {old_str}→{new_str}")
    
    return ", ".join(changes) if changes else "No changes detected"
