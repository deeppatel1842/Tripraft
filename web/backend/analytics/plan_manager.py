"""
Subscription Plan Manager
=========================
Manages free and paid tier limits, usage tracking, and plan enforcement.

FREE PLAN LIMITS:
- 3 expenses per day
- Unlimited groups (but limited expenses)
- Basic features

PAID PLAN FEATURES:
- Unlimited expenses
- All features unlocked
- Priority support
- PDF export of settlements

Author: Production Team
Date: November 18, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from firebase_admin import firestore
except ImportError:
    firestore = None


class PlanTier(Enum):
    """Subscription tiers"""
    FREE = "free"
    PAID = "paid"
    TRIAL = "trial"


class LimitType(Enum):
    """Types of limits"""
    DAILY_EXPENSES = "daily_expenses"
    GROUPS = "groups"
    MEMBERS_PER_GROUP = "members_per_group"


@dataclass
class PlanLimits:
    """Plan limits configuration"""
    tier: str
    
    # Expense limits
    daily_expense_limit: Optional[int] = None  # None = unlimited
    monthly_expense_limit: Optional[int] = None
    
    # Group limits
    max_groups: Optional[int] = None
    max_members_per_group: Optional[int] = None
    
    # Feature flags
    can_export_pdf: bool = False
    can_schedule_settlements: bool = False
    priority_support: bool = False
    
    # Storage
    max_attachment_size_mb: int = 5


# Plan configurations
FREE_PLAN = PlanLimits(
    tier=PlanTier.FREE.value,
    daily_expense_limit=3,
    monthly_expense_limit=90,  # 3 per day * 30 days
    max_groups=None,  # Unlimited groups
    max_members_per_group=10,
    can_export_pdf=False,
    can_schedule_settlements=False,
    priority_support=False,
    max_attachment_size_mb=5
)

PAID_PLAN = PlanLimits(
    tier=PlanTier.PAID.value,
    daily_expense_limit=None,  # Unlimited
    monthly_expense_limit=None,  # Unlimited
    max_groups=None,  # Unlimited
    max_members_per_group=None,  # Unlimited
    can_export_pdf=True,
    can_schedule_settlements=True,
    priority_support=True,
    max_attachment_size_mb=50
)


class PlanManager:
    """Manages subscription plans and enforces limits"""
    
    def __init__(self, db=None):
        """
        Initialize plan manager
        
        Args:
            db: Firestore database instance
        """
        self.db = db
        self.usage_collection = "user_daily_usage"
        self.users_collection = "users"
    
    # ==================== PLAN MANAGEMENT ====================
    
    def get_user_plan(self, user_id: str) -> PlanLimits:
        """
        Get plan limits for a user
        
        Args:
            user_id: User ID
            
        Returns:
            PlanLimits object
        """
        if not self.db:
            return FREE_PLAN
        
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return FREE_PLAN
            
            user_data = user_doc.to_dict()
            tier = user_data.get("subscription_tier", "free")
            
            if tier == PlanTier.PAID.value:
                return PAID_PLAN
            else:
                return FREE_PLAN
        
        except Exception as e:
            print(f"Error getting user plan: {e}")
            return FREE_PLAN
    
    def upgrade_user_to_paid(self, user_id: str) -> bool:
        """
        Upgrade user to paid plan
        
        Args:
            user_id: User ID
            
        Returns:
            bool: Success status
        """
        if not self.db:
            return False
        
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_ref.update({
                "subscription_tier": PlanTier.PAID.value,
                "upgraded_at": datetime.utcnow(),
                "subscription_status": "active"
            })
            
            # Track analytics event
            from analytics.analytics_engine import AnalyticsEngine, EventType
            analytics = AnalyticsEngine(self.db)
            analytics.track_event(
                EventType.UPGRADE_TO_PAID,
                user_id,
                properties={"from_tier": "free", "to_tier": "paid"}
            )
            
            return True
        
        except Exception as e:
            print(f"Error upgrading user: {e}")
            return False
    
    # ==================== USAGE TRACKING ====================
    
    def get_daily_usage(self, user_id: str, date: Optional[datetime] = None) -> Dict[str, int]:
        """
        Get user's usage for a specific date
        
        Args:
            user_id: User ID
            date: Date to check (default: today)
            
        Returns:
            Dict with usage counts
        """
        if not self.db:
            return {"expenses_created": 0}
        
        target_date = date or datetime.utcnow()
        date_str = target_date.strftime("%Y-%m-%d")
        doc_id = f"{user_id}_{date_str}"
        
        try:
            usage_ref = self.db.collection(self.usage_collection).document(doc_id)
            usage_doc = usage_ref.get()
            
            if usage_doc.exists:
                return usage_doc.to_dict()
            else:
                return {
                    "user_id": user_id,
                    "date": date_str,
                    "expenses_created": 0,
                    "groups_created": 0,
                    "invitations_sent": 0
                }
        
        except Exception as e:
            print(f"Error getting daily usage: {e}")
            return {"expenses_created": 0}
    
    def increment_usage(
        self,
        user_id: str,
        usage_type: str,
        increment: int = 1
    ) -> bool:
        """
        Increment usage counter for a user
        
        Args:
            user_id: User ID
            usage_type: Type of usage (expenses_created, groups_created, etc.)
            increment: Amount to increment
            
        Returns:
            bool: Success status
        """
        if not self.db:
            return False
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        doc_id = f"{user_id}_{date_str}"
        
        try:
            usage_ref = self.db.collection(self.usage_collection).document(doc_id)
            usage_doc = usage_ref.get()
            
            if usage_doc.exists:
                current_value = usage_doc.to_dict().get(usage_type, 0)
                usage_ref.update({usage_type: current_value + increment})
            else:
                usage_ref.set({
                    "user_id": user_id,
                    "date": date_str,
                    usage_type: increment,
                    "created_at": datetime.utcnow()
                })
            
            return True
        
        except Exception as e:
            print(f"Error incrementing usage: {e}")
            return False
    
    # ==================== LIMIT ENFORCEMENT ====================
    
    def can_create_expense(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user can create an expense
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple[bool, Optional[str]]: (can_create, error_message)
        """
        plan = self.get_user_plan(user_id)
        
        # Paid users have unlimited expenses
        if plan.tier == PlanTier.PAID.value:
            return (True, None)
        
        # Check daily limit for free users
        if plan.daily_expense_limit is not None:
            usage = self.get_daily_usage(user_id)
            expenses_today = usage.get("expenses_created", 0)
            
            if expenses_today >= plan.daily_expense_limit:
                return (
                    False,
                    f"Daily expense limit reached ({plan.daily_expense_limit} expenses per day). "
                    f"Upgrade to paid plan for unlimited expenses."
                )
        
        return (True, None)
    
    def can_create_group(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user can create a group
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple[bool, Optional[str]]: (can_create, error_message)
        """
        plan = self.get_user_plan(user_id)
        
        # Check group limit
        if plan.max_groups is not None:
            # TODO: Count user's current groups
            # For now, assume allowed
            pass
        
        return (True, None)
    
    def can_add_group_member(
        self,
        user_id: str,
        group_id: str,
        current_member_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user can add another member to group
        
        Args:
            user_id: User ID
            group_id: Group ID
            current_member_count: Current number of members
            
        Returns:
            Tuple[bool, Optional[str]]: (can_add, error_message)
        """
        plan = self.get_user_plan(user_id)
        
        if plan.max_members_per_group is not None:
            if current_member_count >= plan.max_members_per_group:
                return (
                    False,
                    f"Group member limit reached ({plan.max_members_per_group} members). "
                    f"Upgrade to paid plan for unlimited members."
                )
        
        return (True, None)
    
    def can_export_pdf(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user can export PDF
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple[bool, Optional[str]]: (can_export, error_message)
        """
        plan = self.get_user_plan(user_id)
        
        if not plan.can_export_pdf:
            return (
                False,
                "PDF export is only available for paid users. Upgrade to unlock this feature."
            )
        
        return (True, None)
    
    # ==================== USAGE ANALYTICS ====================
    
    def get_usage_summary(self, user_id: str, days: int = 30) -> Dict[str, any]:
        """
        Get usage summary for past N days
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Dict with usage statistics
        """
        if not self.db:
            return {}
        
        summary = {
            "total_expenses": 0,
            "total_groups": 0,
            "total_invitations": 0,
            "daily_breakdown": []
        }
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            for i in range(days):
                check_date = start_date + timedelta(days=i)
                usage = self.get_daily_usage(user_id, check_date)
                
                summary["total_expenses"] += usage.get("expenses_created", 0)
                summary["total_groups"] += usage.get("groups_created", 0)
                summary["total_invitations"] += usage.get("invitations_sent", 0)
                
                summary["daily_breakdown"].append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "expenses": usage.get("expenses_created", 0)
                })
            
            return summary
        
        except Exception as e:
            print(f"Error getting usage summary: {e}")
            return summary
    
    def get_limit_info(self, user_id: str) -> Dict[str, any]:
        """
        Get current limits and usage for user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with limit information
        """
        plan = self.get_user_plan(user_id)
        usage = self.get_daily_usage(user_id)
        
        expenses_used = usage.get("expenses_created", 0)
        
        return {
            "tier": plan.tier,
            "daily_expenses": {
                "limit": plan.daily_expense_limit,
                "used": expenses_used,
                "remaining": (
                    plan.daily_expense_limit - expenses_used
                    if plan.daily_expense_limit is not None
                    else None  # Unlimited
                ),
                "is_unlimited": plan.daily_expense_limit is None
            },
            "features": {
                "pdf_export": plan.can_export_pdf,
                "schedule_settlements": plan.can_schedule_settlements,
                "priority_support": plan.priority_support
            },
            "upgrade_available": plan.tier == PlanTier.FREE.value
        }


# ==================== HELPER FUNCTIONS ====================

def check_and_track_expense_creation(db, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user can create expense and track usage
    
    Args:
        db: Firestore database
        user_id: User ID
        
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    manager = PlanManager(db)
    
    # Check if user can create expense
    can_create, error = manager.can_create_expense(user_id)
    
    if not can_create:
        # Track limit reached event
        from analytics.analytics_engine import AnalyticsEngine, EventType
        analytics = AnalyticsEngine(db)
        analytics.track_event(
            EventType.EXPENSE_LIMIT_REACHED,
            user_id,
            properties={"limit_type": "daily_expenses"}
        )
        
        return (False, error)
    
    # Increment usage counter
    manager.increment_usage(user_id, "expenses_created")
    
    return (True, None)
