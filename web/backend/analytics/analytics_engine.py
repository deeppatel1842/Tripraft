"""
Analytics Engine for Expense Tracker
=====================================
Tracks user behavior, engagement metrics, and business KPIs.

Features:
- User activity tracking (DAU, WAU, MAU)
- Session duration and frequency
- Feature usage metrics
- Retention cohorts
- Revenue analytics (free vs paid)
- Expense creation patterns
- Settlement completion rates

Author: Production Team
Date: November 18, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    from firebase_admin import firestore
except ImportError:
    firestore = None


class UserTier(Enum):
    """User subscription tiers"""
    FREE = "free"
    PAID = "paid"
    TRIAL = "trial"


class EventType(Enum):
    """Analytics event types"""
    # User events
    USER_SIGNUP = "user_signup"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    
    # Expense events
    EXPENSE_CREATED = "expense_created"
    EXPENSE_EDITED = "expense_edited"
    EXPENSE_DELETED = "expense_deleted"
    EXPENSE_LIMIT_REACHED = "expense_limit_reached"
    
    # Group events
    GROUP_CREATED = "group_created"
    GROUP_JOINED = "group_joined"
    GROUP_LEFT = "group_left"
    
    # Settlement events
    SETTLEMENT_CREATED = "settlement_created"
    SETTLEMENT_COMPLETED = "settlement_completed"
    SETTLEMENT_ARCHIVED = "settlement_archived"
    
    # Invitation events
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_DECLINED = "invitation_declined"
    
    # Subscription events
    UPGRADE_TO_PAID = "upgrade_to_paid"
    DOWNGRADE_TO_FREE = "downgrade_to_free"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    
    # Feature usage
    PDF_GENERATED = "pdf_generated"
    EMAIL_SENT = "email_sent"
    NOTIFICATION_CLICKED = "notification_clicked"


@dataclass
class AnalyticsEvent:
    """Single analytics event"""
    event_type: str
    user_id: str
    timestamp: datetime
    properties: Dict[str, Any]
    session_id: Optional[str] = None
    user_tier: Optional[str] = None
    device_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class UserMetrics:
    """User engagement metrics"""
    user_id: str
    tier: str
    
    # Activity metrics
    total_sessions: int = 0
    total_time_spent_minutes: int = 0
    avg_session_duration_minutes: float = 0.0
    last_active: Optional[datetime] = None
    
    # Expense metrics
    total_expenses_created: int = 0
    total_expenses_today: int = 0
    total_amount_tracked: float = 0.0
    
    # Group metrics
    groups_created: int = 0
    groups_joined: int = 0
    active_groups: int = 0
    
    # Settlement metrics
    settlements_completed: int = 0
    total_settled_amount: float = 0.0
    
    # Engagement metrics
    days_active_this_week: int = 0
    days_active_this_month: int = 0
    streak_days: int = 0
    
    # Conversion metrics
    days_since_signup: int = 0
    upgraded_to_paid: bool = False
    upgrade_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        if self.last_active:
            data['last_active'] = self.last_active.isoformat()
        if self.upgrade_date:
            data['upgrade_date'] = self.upgrade_date.isoformat()
        return data


@dataclass
class BusinessMetrics:
    """Business KPIs and analytics"""
    date: datetime
    
    # User metrics
    total_users: int = 0
    new_users_today: int = 0
    active_users_today: int = 0  # DAU
    active_users_week: int = 0   # WAU
    active_users_month: int = 0  # MAU
    
    # Tier breakdown
    free_users: int = 0
    paid_users: int = 0
    trial_users: int = 0
    
    # Conversion metrics
    free_to_paid_conversions: int = 0
    conversion_rate: float = 0.0
    
    # Revenue metrics (if applicable)
    monthly_recurring_revenue: float = 0.0
    average_revenue_per_user: float = 0.0
    
    # Engagement metrics
    total_expenses_created: int = 0
    total_settlements_completed: int = 0
    avg_session_duration_minutes: float = 0.0
    
    # Retention metrics
    day_1_retention: float = 0.0
    day_7_retention: float = 0.0
    day_30_retention: float = 0.0
    
    # Feature usage
    pdf_downloads: int = 0
    invitations_sent: int = 0
    groups_created: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['date'] = self.date.isoformat()
        return data


class AnalyticsEngine:
    """Main analytics engine"""
    
    def __init__(self, db=None):
        """
        Initialize analytics engine
        
        Args:
            db: Firestore database instance
        """
        self.db = db
        self.events_collection = "analytics_events"
        self.metrics_collection = "user_metrics"
        self.business_metrics_collection = "business_metrics"
        self.sessions_collection = "user_sessions"
    
    # ==================== EVENT TRACKING ====================
    
    def track_event(
        self,
        event_type: EventType,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_tier: Optional[str] = None
    ) -> bool:
        """
        Track a single analytics event
        
        Args:
            event_type: Type of event
            user_id: User ID
            properties: Additional event properties
            session_id: Session identifier
            user_tier: User subscription tier
            
        Returns:
            bool: Success status
        """
        if not self.db:
            return False
        
        event = AnalyticsEvent(
            event_type=event_type.value,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            properties=properties or {},
            session_id=session_id,
            user_tier=user_tier
        )
        
        try:
            self.db.collection(self.events_collection).add(event.to_dict())
            
            # Update user metrics asynchronously
            self._update_user_metrics(user_id, event_type, properties)
            
            return True
        except Exception as e:
            print(f"Error tracking event: {e}")
            return False
    
    def track_expense_created(
        self,
        user_id: str,
        expense_id: str,
        amount: float,
        group_id: str,
        user_tier: str
    ):
        """Track expense creation event"""
        self.track_event(
            EventType.EXPENSE_CREATED,
            user_id,
            properties={
                "expense_id": expense_id,
                "amount": amount,
                "group_id": group_id
            },
            user_tier=user_tier
        )
    
    def track_settlement_completed(
        self,
        user_id: str,
        settlement_id: str,
        amount: float,
        group_id: str
    ):
        """Track settlement completion"""
        self.track_event(
            EventType.SETTLEMENT_COMPLETED,
            user_id,
            properties={
                "settlement_id": settlement_id,
                "amount": amount,
                "group_id": group_id
            }
        )
    
    def track_upgrade(self, user_id: str, from_tier: str, to_tier: str):
        """Track user tier upgrade"""
        self.track_event(
            EventType.UPGRADE_TO_PAID,
            user_id,
            properties={
                "from_tier": from_tier,
                "to_tier": to_tier
            },
            user_tier=to_tier
        )
    
    # ==================== USER METRICS ====================
    
    def _update_user_metrics(
        self,
        user_id: str,
        event_type: EventType,
        properties: Optional[Dict[str, Any]]
    ):
        """Update user metrics based on event"""
        if not self.db:
            return
        
        try:
            user_metrics_ref = self.db.collection(self.metrics_collection).document(user_id)
            user_metrics_doc = user_metrics_ref.get()
            
            if user_metrics_doc.exists:
                metrics = user_metrics_doc.to_dict()
            else:
                metrics = {
                    "user_id": user_id,
                    "total_expenses_created": 0,
                    "total_expenses_today": 0,
                    "settlements_completed": 0,
                    "groups_created": 0,
                    "last_active": datetime.utcnow().isoformat()
                }
            
            # Update based on event type
            if event_type == EventType.EXPENSE_CREATED:
                metrics["total_expenses_created"] = metrics.get("total_expenses_created", 0) + 1
                metrics["total_expenses_today"] = metrics.get("total_expenses_today", 0) + 1
                if properties and "amount" in properties:
                    metrics["total_amount_tracked"] = metrics.get("total_amount_tracked", 0) + properties["amount"]
            
            elif event_type == EventType.SETTLEMENT_COMPLETED:
                metrics["settlements_completed"] = metrics.get("settlements_completed", 0) + 1
                if properties and "amount" in properties:
                    metrics["total_settled_amount"] = metrics.get("total_settled_amount", 0) + properties["amount"]
            
            elif event_type == EventType.GROUP_CREATED:
                metrics["groups_created"] = metrics.get("groups_created", 0) + 1
            
            elif event_type == EventType.UPGRADE_TO_PAID:
                metrics["upgraded_to_paid"] = True
                metrics["upgrade_date"] = datetime.utcnow().isoformat()
            
            metrics["last_active"] = datetime.utcnow().isoformat()
            
            user_metrics_ref.set(metrics, merge=True)
        
        except Exception as e:
            print(f"Error updating user metrics: {e}")
    
    def get_user_metrics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user metrics or None
        """
        if not self.db:
            return None
        
        try:
            user_metrics_ref = self.db.collection(self.metrics_collection).document(user_id)
            doc = user_metrics_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
        
        except Exception as e:
            print(f"Error getting user metrics: {e}")
            return None
    
    # ==================== BUSINESS METRICS ====================
    
    def calculate_daily_metrics(self, date: Optional[datetime] = None) -> BusinessMetrics:
        """
        Calculate business metrics for a specific date
        
        Args:
            date: Date to calculate metrics for (default: today)
            
        Returns:
            BusinessMetrics object
        """
        if not self.db:
            return BusinessMetrics(date=datetime.utcnow())
        
        target_date = date or datetime.utcnow()
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        metrics = BusinessMetrics(date=target_date)
        
        try:
            # Get all users
            users_ref = self.db.collection("users")
            all_users = users_ref.stream()
            
            for user in all_users:
                user_data = user.to_dict()
                metrics.total_users += 1
                
                # Tier breakdown
                tier = user_data.get("tier", "free")
                if tier == "free":
                    metrics.free_users += 1
                elif tier == "paid":
                    metrics.paid_users += 1
                elif tier == "trial":
                    metrics.trial_users += 1
                
                # Check if new user today
                created_at = user_data.get("created_at")
                if created_at and isinstance(created_at, datetime):
                    if start_of_day <= created_at < end_of_day:
                        metrics.new_users_today += 1
            
            # Get events for today
            events_ref = self.db.collection(self.events_collection)
            today_events = events_ref.where(
                "timestamp", ">=", start_of_day.isoformat()
            ).where(
                "timestamp", "<", end_of_day.isoformat()
            ).stream()
            
            active_users_today = set()
            
            for event in today_events:
                event_data = event.to_dict()
                event_type = event_data.get("event_type")
                user_id = event_data.get("user_id")
                
                if user_id:
                    active_users_today.add(user_id)
                
                if event_type == "expense_created":
                    metrics.total_expenses_created += 1
                elif event_type == "settlement_completed":
                    metrics.total_settlements_completed += 1
                elif event_type == "upgrade_to_paid":
                    metrics.free_to_paid_conversions += 1
                elif event_type == "pdf_generated":
                    metrics.pdf_downloads += 1
                elif event_type == "invitation_sent":
                    metrics.invitations_sent += 1
                elif event_type == "group_created":
                    metrics.groups_created += 1
            
            metrics.active_users_today = len(active_users_today)
            
            # Calculate conversion rate
            if metrics.free_users > 0:
                metrics.conversion_rate = (metrics.paid_users / metrics.total_users) * 100
            
            # Save metrics to database
            self.db.collection(self.business_metrics_collection).add(metrics.to_dict())
            
            return metrics
        
        except Exception as e:
            print(f"Error calculating daily metrics: {e}")
            return metrics
    
    def get_metrics_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get business metrics for a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of daily metrics
        """
        if not self.db:
            return []
        
        try:
            metrics_ref = self.db.collection(self.business_metrics_collection)
            docs = metrics_ref.where(
                "date", ">=", start_date.isoformat()
            ).where(
                "date", "<=", end_date.isoformat()
            ).order_by("date").stream()
            
            return [doc.to_dict() for doc in docs]
        
        except Exception as e:
            print(f"Error getting metrics range: {e}")
            return []
    
    # ==================== RETENTION ANALYSIS ====================
    
    def calculate_retention_cohort(
        self,
        signup_date: datetime,
        retention_days: int = 30
    ) -> Dict[str, float]:
        """
        Calculate retention for users who signed up on a specific date
        
        Args:
            signup_date: Date of user signup
            retention_days: Number of days to track retention
            
        Returns:
            Dict with retention percentages by day
        """
        if not self.db:
            return {}
        
        try:
            start_of_day = signup_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # Get users who signed up on this date
            users_ref = self.db.collection("users")
            cohort_users = users_ref.where(
                "created_at", ">=", start_of_day
            ).where(
                "created_at", "<", end_of_day
            ).stream()
            
            user_ids = [user.id for user in cohort_users]
            cohort_size = len(user_ids)
            
            if cohort_size == 0:
                return {}
            
            retention = {}
            
            # Check retention for each day
            for day in [1, 7, 14, 30]:
                if day > retention_days:
                    break
                
                check_date = start_of_day + timedelta(days=day)
                next_day = check_date + timedelta(days=1)
                
                # Count users active on this day
                events_ref = self.db.collection(self.events_collection)
                active_users = events_ref.where(
                    "user_id", "in", user_ids[:10]  # Firestore limit
                ).where(
                    "timestamp", ">=", check_date.isoformat()
                ).where(
                    "timestamp", "<", next_day.isoformat()
                ).stream()
                
                active_count = len(set([event.to_dict()["user_id"] for event in active_users]))
                retention[f"day_{day}"] = (active_count / cohort_size) * 100
            
            return retention
        
        except Exception as e:
            print(f"Error calculating retention: {e}")
            return {}
    
    # ==================== SESSION TRACKING ====================
    
    def start_session(self, user_id: str, device_type: str = "web") -> str:
        """
        Start a new user session
        
        Args:
            user_id: User ID
            device_type: Device type (web, mobile, etc.)
            
        Returns:
            str: Session ID
        """
        if not self.db:
            return ""
        
        try:
            session_data = {
                "user_id": user_id,
                "start_time": datetime.utcnow(),
                "device_type": device_type,
                "active": True
            }
            
            session_ref = self.db.collection(self.sessions_collection).add(session_data)
            return session_ref[1].id
        
        except Exception as e:
            print(f"Error starting session: {e}")
            return ""
    
    def end_session(self, session_id: str):
        """
        End a user session
        
        Args:
            session_id: Session ID
        """
        if not self.db:
            return
        
        try:
            session_ref = self.db.collection(self.sessions_collection).document(session_id)
            session_ref.update({
                "end_time": datetime.utcnow(),
                "active": False
            })
        
        except Exception as e:
            print(f"Error ending session: {e}")


# ==================== HELPER FUNCTIONS ====================

def get_analytics_summary(db, user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive analytics summary for a user
    
    Args:
        db: Firestore database
        user_id: User ID
        
    Returns:
        Dict with analytics summary
    """
    engine = AnalyticsEngine(db)
    metrics = engine.get_user_metrics(user_id)
    
    if not metrics:
        return {
            "user_id": user_id,
            "message": "No analytics data available"
        }
    
    return {
        "user_id": user_id,
        "engagement": {
            "total_expenses": metrics.get("total_expenses_created", 0),
            "total_amount_tracked": metrics.get("total_amount_tracked", 0),
            "settlements_completed": metrics.get("settlements_completed", 0),
            "groups_created": metrics.get("groups_created", 0)
        },
        "activity": {
            "last_active": metrics.get("last_active"),
            "days_active_this_month": metrics.get("days_active_this_month", 0)
        },
        "subscription": {
            "tier": metrics.get("tier", "free"),
            "upgraded_to_paid": metrics.get("upgraded_to_paid", False)
        }
    }
