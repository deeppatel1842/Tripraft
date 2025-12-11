"""
Expense History Model
Tracks all changes to expenses for audit trail and edit history display
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import Field

from .base import BaseModel


class FieldChange(BaseModel):
    """Represents a single field change"""
    
    field_name: str = Field(..., description="Name of the changed field")
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Optional[Any] = Field(None, description="New value")
    
    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display-friendly format"""
        return {
            "field": self.field_name,
            "old": self._format_value(self.old_value),
            "new": self._format_value(self.new_value)
        }
    
    @staticmethod
    def _format_value(value: Any) -> str:
        """Format value for display"""
        if value is None:
            return "None"
        if isinstance(value, (float, Decimal)):
            return f"${value:.2f}"
        if isinstance(value, datetime):
            return value.strftime("%b %d, %Y %I:%M %p")
        if isinstance(value, list):
            return f"{len(value)} items"
        return str(value)


class ExpenseHistory(BaseModel):
    """
    Track all changes to an expense
    
    Stored in: expense_history/{history_id}
    
    Example:
    {
        "id": "history_abc123",
        "expense_id": "exp_456",
        "group_id": "grp_789",
        "action": "updated",
        "changed_by": "user_123",
        "changed_by_name": "John Doe",
        "changed_at": "2025-11-26T10:30:00Z",
        "changes": [
            {"field_name": "amount", "old_value": 100, "new_value": 150},
            {"field_name": "paid_by", "old_value": "user_A", "new_value": "user_B"}
        ],
        "before_snapshot": {...},
        "after_snapshot": {...}
    }
    """
    
    # Identity
    id: Optional[str] = Field(None, description="Unique history entry ID")
    expense_id: str = Field(..., min_length=1, description="ID of the expense")
    group_id: str = Field(..., min_length=1, description="ID of the group")
    
    # Action type
    action: str = Field(
        ..., 
        pattern="^(created|updated|deleted|restored)$",
        description="Type of change: created, updated, deleted, restored"
    )
    
    # Who made the change
    changed_by: str = Field(..., min_length=1, description="User ID who made the change")
    changed_by_name: Optional[str] = Field(None, max_length=100, description="Display name of user")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # What changed (only for updates)
    changes: List[FieldChange] = Field(
        default_factory=list,
        description="List of field changes"
    )
    
    # Snapshots for full audit trail
    before_snapshot: Optional[Dict[str, Any]] = Field(
        None, 
        description="Complete expense data before change"
    )
    after_snapshot: Dict[str, Any] = Field(
        ..., 
        description="Complete expense data after change"
    )
    
    # Metadata
    ip_address: Optional[str] = Field(None, description="IP address of request")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    
    def get_summary(self) -> str:
        """Get human-readable summary of the change"""
        if self.action == "created":
            return "Created expense"
        elif self.action == "deleted":
            return "Deleted expense"
        elif self.action == "restored":
            return "Restored expense"
        elif self.action == "updated":
            field_names = [c.field_name for c in self.changes]
            if len(field_names) == 1:
                return f"Updated {field_names[0]}"
            elif len(field_names) <= 3:
                return f"Updated {', '.join(field_names)}"
            else:
                return f"Updated {len(field_names)} fields"
        return f"Unknown action: {self.action}"
    
    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to frontend-friendly format"""
        return {
            "id": self.id,
            "expense_id": self.expense_id,
            "action": self.action,
            "changed_by": self.changed_by,
            "changed_by_name": self.changed_by_name,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,  # pylint: disable=no-member
            "summary": self.get_summary(),
            "changes": [c.to_display_dict() for c in self.changes],
            "after_snapshot": self.after_snapshot
        }


def compute_changes(
    before: Optional[Dict[str, Any]], 
    after: Dict[str, Any],
    tracked_fields: Optional[List[str]] = None
) -> List[FieldChange]:
    """
    Compute differences between two expense states
    
    Args:
        before: Previous expense data (None for created)
        after: New expense data
        tracked_fields: Optional list of fields to track (default: all changed fields)
    
    Returns:
        List of FieldChange objects
    """
    if before is None:
        # This is a create - no changes to track
        return []
    
    # Default fields to track changes on
    default_tracked = [
        "description", "amount", "currency", "paid_by", "paid_by_name",
        "split_type", "splits", "category", "notes", "expense_date",
        "is_deleted"
    ]
    
    fields_to_check = tracked_fields or default_tracked
    changes = []
    
    for field in fields_to_check:
        old_val = before.get(field)
        new_val = after.get(field)
        
        # Handle special comparisons
        if _values_differ(old_val, new_val):
            changes.append(FieldChange(
                field_name=field,
                old_value=old_val,
                new_value=new_val
            ))
    
    return changes


def _values_differ(old: Any, new: Any) -> bool:
    """
    Check if two values are meaningfully different
    
    Handles:
    - None vs empty string
    - Float precision issues
    - List ordering (for splits)
    - Datetime comparisons (Phase 17 fix)
    """
    # Both None or empty
    if old is None and new is None:
        return False
    if old == "" and new is None:
        return False
    if old is None and new == "":
        return False
    
    # One is None
    if old is None or new is None:
        return True
    
    # Float comparison with tolerance
    if isinstance(old, (int, float, Decimal)) and isinstance(new, (int, float, Decimal)):
        return abs(float(old) - float(new)) > 0.001
    
    # Phase 17 Fix: Handle datetime comparison properly
    # Convert both to datetime and compare dates (not times)
    if isinstance(old, datetime) or isinstance(new, datetime):
        try:
            old_dt = _to_datetime(old)
            new_dt = _to_datetime(new)
            if old_dt and new_dt:
                # Compare date only (ignore time differences)
                return old_dt.date() != new_dt.date()
        except (ValueError, TypeError, AttributeError):
            pass  # Fall through to string comparison
    
    # Handle string dates (YYYY-MM-DD format or ISO format)
    if isinstance(old, str) and isinstance(new, str):
        # Check if both look like dates
        if (_looks_like_date(old) and _looks_like_date(new)):
            try:
                old_dt = _to_datetime(old)
                new_dt = _to_datetime(new)
                if old_dt and new_dt:
                    return old_dt.date() != new_dt.date()
            except (ValueError, TypeError):
                pass  # Fall through to string comparison
    
    # List comparison (order-independent for splits)
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return True
        # For splits, compare by user_id
        if old and isinstance(old[0], dict) and "user_id" in old[0]:
            old_by_user = {s.get("user_id"): s for s in old}
            new_by_user = {s.get("user_id"): s for s in new}
            if set(old_by_user.keys()) != set(new_by_user.keys()):
                return True
            for user_id in old_by_user:
                if _dict_differs(old_by_user[user_id], new_by_user[user_id]):
                    return True
            return False
        # Simple list comparison
        return old != new
    
    # Dict comparison
    if isinstance(old, dict) and isinstance(new, dict):
        return _dict_differs(old, new)
    
    # Default string comparison
    return str(old) != str(new)


def _to_datetime(value: Any) -> Optional[datetime]:
    """Convert various date formats to datetime object"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try various formats
        for fmt in [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
        ]:
            try:
                return datetime.strptime(value.replace('+00:00', 'Z').rstrip('Z') + 'Z' if 'T' in value else value, fmt if 'T' in value else '%Y-%m-%d')
            except ValueError:
                continue
        # Try fromisoformat as last resort
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
    return None


def _looks_like_date(value: str) -> bool:
    """Check if string looks like a date"""
    if not value:
        return False
    # Check for ISO format or YYYY-MM-DD
    return ('T' in value and '-' in value) or (len(value) == 10 and value.count('-') == 2)


def _dict_differs(old: Dict, new: Dict) -> bool:
    """Deep comparison of dictionaries"""
    if set(old.keys()) != set(new.keys()):
        return True
    for key in old:
        if _values_differ(old[key], new[key]):
            return True
    return False
