# Analytics System - Implementation Guide

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
pip install reportlab firebase-admin
```

### 2. Initialize in Your Main App

```python
# In web/backend/run.py or app initialization

from api.analytics_routes import init_analytics_routes
from firebase_admin import firestore

# Initialize Firebase (if not already done)
db = firestore.client()

# Register analytics routes
init_analytics_routes(app, db)
```

### 3. Add to Existing Expense Creation

```python
# In expense_engine/service.py

from analytics.plan_manager import check_and_track_expense_creation

def create_expense(user_id, expense_data):
    # ADD THIS CHECK
    can_create, error = check_and_track_expense_creation(db, user_id)
    if not can_create:
        return {"error": error, "upgrade_required": True}, 403
    
    # Your existing expense creation code...
```

Done! Users now have 3 expenses/day limit (free plan).

---

## Complete Integration Steps

### Step 1: Database Setup (One-Time)

No schema changes needed! Collections are created automatically:
- `analytics_events`
- `user_metrics`
- `user_daily_usage`
- `business_metrics`
- `archived_settlements`

### Step 2: Add User Tier Field

Update user registration to include subscription tier:

```python
# In auth.py or user registration

user_data = {
    "email": email,
    "name": name,
    "created_at": datetime.utcnow(),
    "subscription_tier": "free",  # ADD THIS
    "subscription_status": "active"
}
```

### Step 3: Integrate Plan Checks

#### A. Expense Creation Limit

```python
# In api/routes.py - Expense creation endpoint

from analytics.plan_manager import PlanManager

@app.route('/api/expenses', methods=['POST'])
@require_auth
def create_expense():
    manager = PlanManager(db)
    
    # Check if user can create expense
    can_create, error = manager.can_create_expense(g.user_id)
    if not can_create:
        return jsonify({
            "error": error,
            "upgrade_required": True,
            "current_plan": "free"
        }), 403
    
    # Create expense...
    expense_id = create_expense_logic(...)
    
    # Track usage
    manager.increment_usage(g.user_id, "expenses_created")
    
    # Track analytics event
    from analytics.analytics_engine import AnalyticsEngine, EventType
    analytics = AnalyticsEngine(db)
    analytics.track_expense_created(
        g.user_id,
        expense_id,
        amount=expense_data['amount'],
        group_id=expense_data['group_id'],
        user_tier="free"  # or get from user profile
    )
    
    return jsonify({"success": True, "expense_id": expense_id})
```

#### B. PDF Export Limit

```python
# In api/routes.py - PDF export endpoint

@app.route('/api/settlements/export/<group_id>', methods=['GET'])
@require_auth
def export_settlement_pdf(group_id):
    manager = PlanManager(db)
    
    # Check if user can export PDF
    can_export, error = manager.can_export_pdf(g.user_id)
    if not can_export:
        return jsonify({
            "error": error,
            "upgrade_required": True,
            "feature": "pdf_export"
        }), 403
    
    # Generate PDF...
    # Use settlement_archiver.generate_settlement_pdf()
```

### Step 4: Frontend Integration

#### Display Plan Limits

```javascript
// In ExpenseManager.jsx or PlanSettings component

const [planLimits, setPlanLimits] = useState(null);

useEffect(() => {
    fetch('/api/plan/limits', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => setPlanLimits(data.data));
}, []);

// Display usage
{planLimits && (
    <div className="plan-usage">
        <h3>{planLimits.tier.toUpperCase()} Plan</h3>
        {!planLimits.daily_expenses.is_unlimited && (
            <p>
                Daily Expenses: {planLimits.daily_expenses.used} / {planLimits.daily_expenses.limit}
                ({planLimits.daily_expenses.remaining} remaining)
            </p>
        )}
        {planLimits.upgrade_available && (
            <button onClick={handleUpgrade}>Upgrade to Paid</button>
        )}
    </div>
)}
```

#### Handle Limit Reached Errors

```javascript
// When creating expense

const createExpense = async (expenseData) => {
    try {
        const response = await fetch('/api/expenses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(expenseData)
        });
        
        const data = await response.json();
        
        if (response.status === 403 && data.upgrade_required) {
            // Show upgrade prompt
            setShowUpgradeModal(true);
            setUpgradeMessage(data.error);
        } else if (data.success) {
            // Success
            showToast('Expense created!');
        }
    } catch (error) {
        console.error(error);
    }
};
```

#### Upgrade Modal Component

```jsx
// components/UpgradeModal.jsx

const UpgradeModal = ({ show, message, onClose }) => {
    const handleUpgrade = async () => {
        const response = await fetch('/api/plan/upgrade', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            showToast('Upgraded to Paid Plan!');
            window.location.reload();
        }
    };
    
    if (!show) return null;
    
    return (
        <div className="modal">
            <div className="modal-content">
                <h2>Upgrade Required</h2>
                <p>{message}</p>
                <div className="upgrade-benefits">
                    <h3>Paid Plan Benefits:</h3>
                    <ul>
                        <li>✅ Unlimited expenses</li>
                        <li>✅ PDF export</li>
                        <li>✅ Scheduled settlements</li>
                        <li>✅ Priority support</li>
                    </ul>
                </div>
                <button onClick={handleUpgrade}>Upgrade Now</button>
                <button onClick={onClose}>Maybe Later</button>
            </div>
        </div>
    );
};
```

### Step 5: Schedule Monthly Archiving

#### Option A: Cloud Functions (Firebase)

```javascript
// functions/index.js

const functions = require('firebase-functions');
const admin = require('firebase-admin');

exports.monthlySettlementArchiving = functions.pubsub
    .schedule('0 0 1 * *')  // First day of every month at midnight
    .timeZone('America/New_York')
    .onRun(async (context) => {
        const db = admin.firestore();
        const bucket = admin.storage().bucket();
        
        // Call Python archiving function
        // Or implement archiving logic in JavaScript
        
        console.log('Monthly archiving completed');
        return null;
    });
```

#### Option B: Cron Job (Server)

```bash
# Add to crontab

# Run on 1st of every month at 2 AM
0 2 1 * * /path/to/venv/bin/python /path/to/monthly_archive_job.py
```

```python
# monthly_archive_job.py

from firebase_admin import firestore, storage, credentials
import firebase_admin

# Initialize Firebase
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-bucket.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()

from analytics.settlement_archiver import SettlementArchiver

archiver = SettlementArchiver(db, bucket)
results = archiver.monthly_archiving_job()

print(f"Archived {results['archived_count']} settlements")
```

### Step 6: Admin Dashboard (Optional)

```python
# In admin dashboard route

@app.route('/admin/analytics', methods=['GET'])
@require_admin
def admin_dashboard():
    from analytics.analytics_engine import AnalyticsEngine
    
    analytics = AnalyticsEngine(db)
    
    # Get today's metrics
    today_metrics = analytics.calculate_daily_metrics()
    
    # Get last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    historical = analytics.get_metrics_range(start_date, end_date)
    
    return render_template('admin_dashboard.html', {
        'today': today_metrics.to_dict(),
        'historical': historical
    })
```

---

## Testing

### Test Plan Limits

```python
# test_plan_limits.py

from analytics.plan_manager import PlanManager, FREE_PLAN, PAID_PLAN

def test_free_user_limit():
    manager = PlanManager(db)
    
    # Create 3 expenses (should succeed)
    for i in range(3):
        can_create, error = manager.can_create_expense("test_user")
        assert can_create is True
        manager.increment_usage("test_user", "expenses_created")
    
    # 4th expense should fail
    can_create, error = manager.can_create_expense("test_user")
    assert can_create is False
    assert "Daily expense limit reached" in error

def test_paid_user_unlimited():
    manager = PlanManager(db)
    
    # Upgrade user
    manager.upgrade_user_to_paid("test_user")
    
    # Create 100 expenses (should all succeed)
    for i in range(100):
        can_create, error = manager.can_create_expense("test_user")
        assert can_create is True
```

### Test Analytics Tracking

```python
# test_analytics.py

from analytics.analytics_engine import AnalyticsEngine, EventType

def test_event_tracking():
    analytics = AnalyticsEngine(db)
    
    # Track expense
    success = analytics.track_expense_created(
        "test_user",
        "expense123",
        45.00,
        "group456",
        "free"
    )
    assert success is True
    
    # Check metrics updated
    metrics = analytics.get_user_metrics("test_user")
    assert metrics['total_expenses_created'] >= 1
```

---

## Monitoring & Maintenance

### Daily Checks

1. **Check usage tracking**
   ```python
   # Get today's stats
   analytics = AnalyticsEngine(db)
   metrics = analytics.calculate_daily_metrics()
   print(f"Active users today: {metrics.active_users_today}")
   print(f"New users: {metrics.new_users_today}")
   ```

2. **Monitor conversion rate**
   ```python
   conversion_rate = metrics.conversion_rate
   if conversion_rate < 10:
       print("⚠️ Low conversion rate!")
   ```

### Monthly Tasks

1. Run archiving job (automatically if scheduled)
2. Review business metrics
3. Check storage usage (PDFs)
4. Analyze retention cohorts

### Performance Tips

1. **Index Firestore collections**
   ```javascript
   // Firestore indexes needed:
   analytics_events: [timestamp, user_id]
   user_daily_usage: [user_id, date]
   settlements: [settled_at, status]
   ```

2. **Batch analytics writes**
   - Analytics writes are non-blocking
   - Use batch operations for bulk updates

3. **Cache frequently accessed data**
   - User tier (Redis: 1 hour TTL)
   - Daily usage (Redis: 5 min TTL)

---

## Troubleshooting

### Issue: "Daily limit not resetting"
**Solution**: Usage is tracked by date. Check your timezone settings in `plan_manager.py`.

### Issue: "PDF generation fails"
**Solution**: Ensure `reportlab` is installed: `pip install reportlab`

### Issue: "Analytics events not appearing"
**Solution**: Check Firebase rules allow writes to `analytics_events` collection.

### Issue: "Email not sending"
**Solution**: Verify email service credentials in `services/email_service.py`.

---

## API Testing with cURL

```bash
# Check plan limits
curl -X GET "http://localhost:5000/api/plan/limits" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Upgrade to paid
curl -X POST "http://localhost:5000/api/plan/upgrade" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Generate settlement PDF
curl -X GET "http://localhost:5000/api/settlements/report/group123?start_date=2025-10-01&end_date=2025-10-31" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output report.pdf

# Get user analytics
curl -X GET "http://localhost:5000/api/analytics/user/user123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

**Need Help?** Check the main README.md for detailed documentation.
