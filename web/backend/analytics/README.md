# Analytics & Business Intelligence System

## Overview

Complete analytics and subscription management system for the expense tracking application.

## 📊 Features

### 1. **Analytics Engine** (`analytics_engine.py`)
Comprehensive user behavior and business metrics tracking:

- **Event Tracking**: 20+ event types (user signup, expense created, settlement completed, etc.)
- **User Metrics**: Session tracking, engagement metrics, retention cohorts
- **Business KPIs**: DAU/WAU/MAU, conversion rates, revenue analytics
- **Custom Events**: Track any custom user actions

**Key Metrics Tracked:**
- Daily/Weekly/Monthly Active Users (DAU/WAU/MAU)
- User session duration and frequency
- Expense creation patterns
- Settlement completion rates
- Free → Paid conversion rates
- Feature usage statistics
- Retention (Day 1, 7, 30)

### 2. **Plan Manager** (`plan_manager.py`)
Subscription tier management and usage enforcement:

**FREE PLAN:**
- ✅ 3 expenses per day
- ✅ Unlimited groups
- ✅ Up to 10 members per group
- ❌ No PDF export
- ❌ No scheduled settlements

**PAID PLAN:**
- ✅ Unlimited expenses
- ✅ Unlimited groups
- ✅ Unlimited members
- ✅ PDF export
- ✅ Scheduled settlements
- ✅ Priority support

**Features:**
- Real-time usage tracking
- Daily/monthly usage limits
- Automatic limit enforcement
- Usage analytics and summaries
- Upgrade/downgrade management

### 3. **Settlement Archiver** (`settlement_archiver.py`)
Automated settlement archiving and PDF generation:

**Features:**
- Archive settlements older than 30 days
- Generate professional PDF reports
- Email PDF to all group members
- Scheduled monthly archiving
- Secure storage in Firebase Storage

**PDF Report Includes:**
- Group name and date range
- Total settlements count
- Total amount settled
- Individual settlement details
- Payer/payee information
- Professional formatting

### 4. **API Routes** (`analytics_routes.py`)
RESTful API endpoints for all analytics features:

```
GET  /api/analytics/user/{user_id}      - User analytics
GET  /api/analytics/dashboard           - Business metrics (admin)
POST /api/analytics/track               - Track custom events
GET  /api/plan/limits                   - Current plan limits
GET  /api/plan/usage                    - Usage summary
POST /api/plan/upgrade                  - Upgrade to paid
GET  /api/plan/check-limit/{type}       - Check specific limit
POST /api/settlements/archive           - Trigger archiving (admin)
GET  /api/settlements/report/{group_id} - Generate PDF report
```

## 🚀 Usage Examples

### Track Expense Creation with Limit Check

```python
from firebase_admin import firestore
from analytics.plan_manager import check_and_track_expense_creation
from analytics.analytics_engine import AnalyticsEngine, EventType

db = firestore.client()

# Check if user can create expense (enforces FREE plan 3/day limit)
can_create, error = check_and_track_expense_creation(db, user_id)

if not can_create:
    return {"error": error, "upgrade_required": True}, 403

# Create expense...
# Automatically tracked and usage incremented
```

### Generate Monthly Settlement Report

```python
from analytics.settlement_archiver import generate_and_send_monthly_report
from firebase_admin import firestore, storage

db = firestore.client()
bucket = storage.bucket()

# Generate and email PDF report for last month
success = generate_and_send_monthly_report(
    db,
    bucket,
    group_id="group123",
    member_emails=["user1@example.com", "user2@example.com"]
)
```

### Get User Analytics Dashboard

```python
from analytics.analytics_engine import get_analytics_summary

summary = get_analytics_summary(db, user_id)

# Returns:
# {
#     "user_id": "...",
#     "engagement": {
#         "total_expenses": 145,
#         "total_amount_tracked": 5240.50,
#         "settlements_completed": 12,
#         "groups_created": 3
#     },
#     "activity": {
#         "last_active": "2025-11-18T10:30:00",
#         "days_active_this_month": 18
#     },
#     "subscription": {
#         "tier": "free",
#         "upgraded_to_paid": false
#     }
# }
```

### Check Plan Limits Before Action

```python
from analytics.plan_manager import PlanManager

manager = PlanManager(db)

# Check if user can create expense
can_create, error = manager.can_create_expense(user_id)
if not can_create:
    print(error)  # "Daily expense limit reached (3 expenses per day). Upgrade to paid plan..."

# Check if user can export PDF
can_export, error = manager.can_export_pdf(user_id)
if not can_export:
    print(error)  # "PDF export is only available for paid users..."
```

### Track Custom Events

```python
from analytics.analytics_engine import AnalyticsEngine, EventType

analytics = AnalyticsEngine(db)

# Track expense creation
analytics.track_expense_created(
    user_id="user123",
    expense_id="exp456",
    amount=45.00,
    group_id="group789",
    user_tier="free"
)

# Track upgrade
analytics.track_upgrade(
    user_id="user123",
    from_tier="free",
    to_tier="paid"
)

# Track settlement completion
analytics.track_settlement_completed(
    user_id="user123",
    settlement_id="settle123",
    amount=100.00,
    group_id="group789"
)
```

## 🔧 Integration Steps

### 1. Add Analytics to Expense Creation

In `expense_engine/service.py`:

```python
from analytics.plan_manager import check_and_track_expense_creation

def create_expense(user_id, expense_data):
    # Check limits and track usage
    can_create, error = check_and_track_expense_creation(db, user_id)
    if not can_create:
        return {"error": error, "upgrade_required": True}, 403
    
    # Create expense normally...
    # Usage already tracked by check_and_track_expense_creation()
```

### 2. Add Settlement Tracking

In `expense_engine/service.py`:

```python
from analytics.analytics_engine import AnalyticsEngine, EventType

def mark_settlement_paid(settlement_id):
    # Mark as paid...
    
    # Track analytics
    analytics = AnalyticsEngine(db)
    analytics.track_settlement_completed(
        user_id=payer_id,
        settlement_id=settlement_id,
        amount=amount,
        group_id=group_id
    )
```

### 3. Add Plan Limit Checks to Routes

In `api/routes.py`:

```python
from analytics.plan_manager import PlanManager

@app.route('/api/expenses', methods=['POST'])
def create_expense():
    manager = PlanManager(db)
    
    # Check limit before processing
    can_create, error = manager.can_create_expense(g.user_id)
    if not can_create:
        return jsonify({
            "error": error,
            "upgrade_required": True
        }), 403
    
    # Process expense...
    manager.increment_usage(g.user_id, "expenses_created")
```

### 4. Schedule Monthly Archiving

Create a Cloud Function or cron job:

```python
# cloud_functions/monthly_archive.py
from analytics.settlement_archiver import SettlementArchiver

def monthly_archiving_function(event, context):
    """Scheduled function to run monthly"""
    archiver = SettlementArchiver(db, bucket)
    results = archiver.monthly_archiving_job()
    
    print(f"Archived {results['archived_count']} settlements")
    return results
```

## 📈 Business Metrics Dashboard

### Key Metrics Available:

1. **User Growth**
   - Total users
   - New signups (daily/weekly/monthly)
   - Active users (DAU/WAU/MAU)

2. **Engagement**
   - Avg session duration
   - Sessions per user
   - Feature usage rates
   - Expense creation frequency

3. **Conversion**
   - Free → Paid conversion rate
   - Upgrade funnel metrics
   - Revenue per user (ARPU)

4. **Retention**
   - Day 1, 7, 30 retention
   - Cohort analysis
   - Churn rate

5. **Feature Usage**
   - PDF downloads
   - Settlements completed
   - Groups created
   - Invitations sent

## 🔐 Security & Privacy

- User data anonymization in analytics
- Admin-only access to business metrics
- Secure PDF storage with expiring URLs
- Email delivery via authenticated service
- Rate limiting on analytics endpoints

## 📝 Database Schema

### Collections Created:

**analytics_events** - Event tracking
```javascript
{
    event_type: "expense_created",
    user_id: "user123",
    timestamp: Timestamp,
    properties: {...},
    session_id: "session456",
    user_tier: "free"
}
```

**user_metrics** - Aggregated user metrics
```javascript
{
    user_id: "user123",
    total_expenses_created: 45,
    total_expenses_today: 2,
    total_amount_tracked: 1250.00,
    settlements_completed: 8,
    last_active: Timestamp,
    upgraded_to_paid: false
}
```

**user_daily_usage** - Daily usage tracking
```javascript
{
    // Document ID: user123_2025-11-18
    user_id: "user123",
    date: "2025-11-18",
    expenses_created: 2,
    groups_created: 0,
    invitations_sent: 3
}
```

**business_metrics** - Daily business KPIs
```javascript
{
    date: "2025-11-18",
    total_users: 1250,
    new_users_today: 15,
    active_users_today: 340,
    free_users: 980,
    paid_users: 270,
    conversion_rate: 21.6,
    total_expenses_created: 1840
}
```

**archived_settlements** - Archived settlements (>30 days old)
```javascript
{
    original_id: "settle123",
    group_id: "group789",
    payer_id: "user123",
    payee_id: "user456",
    amount: 50.00,
    settled_at: Timestamp,
    archived_at: Timestamp
}
```

## 🎯 Future Enhancements

1. **Advanced Analytics**
   - Predictive churn models
   - Cohort behavior analysis
   - A/B testing framework

2. **Payment Integration**
   - Stripe/PayPal integration
   - Subscription billing
   - Trial periods

3. **Enhanced Reporting**
   - Custom date ranges
   - Export to Excel/CSV
   - Scheduled email reports

4. **AI/ML Features**
   - Spending predictions
   - Anomaly detection
   - Smart settlement suggestions

## 📞 API Response Examples

### GET /api/plan/limits
```json
{
    "success": true,
    "data": {
        "tier": "free",
        "daily_expenses": {
            "limit": 3,
            "used": 2,
            "remaining": 1,
            "is_unlimited": false
        },
        "features": {
            "pdf_export": false,
            "schedule_settlements": false,
            "priority_support": false
        },
        "upgrade_available": true
    }
}
```

### GET /api/analytics/user/{user_id}
```json
{
    "success": true,
    "data": {
        "user_id": "user123",
        "engagement": {
            "total_expenses": 145,
            "total_amount_tracked": 5240.50,
            "settlements_completed": 12,
            "groups_created": 3
        },
        "activity": {
            "last_active": "2025-11-18T10:30:00Z",
            "days_active_this_month": 18
        },
        "subscription": {
            "tier": "free",
            "upgraded_to_paid": false
        }
    }
}
```

## 🐛 Error Handling

All API endpoints return standardized error responses:

```json
{
    "success": false,
    "error": "Daily expense limit reached (3 expenses per day)",
    "upgrade_required": true
}
```

---

**Created by**: Production Team  
**Date**: November 18, 2025  
**Version**: 1.0.0
