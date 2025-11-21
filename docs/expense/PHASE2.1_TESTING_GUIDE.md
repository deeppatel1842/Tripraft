# Phase 2.1 Testing Guide - Email Worker

**Purpose:** Verify email worker implementation and performance improvements  
**Duration:** 15-20 minutes  
**Prerequisites:** Backend running, authenticated user, test group with expenses

---

## 🎯 Testing Objectives

1. ✅ Verify delete operation is now fast (<500ms)
2. ✅ Confirm emails are queued (not blocking)
3. ✅ Validate email worker processes queue
4. ✅ Check worker health monitoring
5. ✅ Ensure no breaking changes

---

## 🧪 Test Cases

### Test 1: Delete Expense (Primary Goal)

**Objective:** Verify 9x performance improvement (2755ms → ~300ms)

**Steps:**
```bash
# 1. Create a test expense
POST /api/expense/expenses
Authorization: Bearer <token>
{
  "group_id": "<group_id>",
  "description": "Test Email Worker",
  "amount": 50.00,
  "paid_by": "<user_id>",
  "splits": [
    {"user_id": "<user_id>", "amount": 25.00},
    {"user_id": "<other_user_id>", "amount": 25.00}
  ]
}

# 2. Delete the expense
DELETE /api/expense/expenses/<expense_id>
Authorization: Bearer <token>

# 3. Measure response time
```

**Expected Results:**
- ✅ Response time: <500ms (should be ~300ms)
- ✅ Response: `{"success": true, "message": "Expense deleted"}`
- ✅ HTTP Status: 200

**Check Logs:**
```
📧 SCHEDULING DELETE NOTIFICATIONS (email worker)
   ✅ Queued 1 delete notifications
✅ EXPENSE DELETED SUCCESSFULLY
```

**Before/After Comparison:**
| Metric | Before (Week 1) | After (Week 2) | Improvement |
|--------|----------------|----------------|-------------|
| Response Time | 2755ms | ~300ms | 9x faster ⚡ |

---

### Test 2: Create Expense with Notifications

**Objective:** Verify email sending doesn't block create operation

**Steps:**
```bash
POST /api/expense/expenses
Authorization: Bearer <token>
{
  "group_id": "<group_id>",
  "description": "Test Async Email",
  "amount": 100.00,
  "paid_by": "<user_id>",
  "splits": [
    {"user_id": "<user_id>", "amount": 50.00},
    {"user_id": "<other_user_id>", "amount": 50.00}
  ]
}
```

**Expected Results:**
- ✅ Response time: <300ms (was <250ms, should be similar)
- ✅ Response includes expense with optimistic balance
- ✅ HTTP Status: 201

**Check Logs:**
```
📧 Queued 1 expense notifications
```

---

### Test 3: Settlement with Notification

**Objective:** Verify settlement emails are queued, not blocking

**Steps:**
```bash
POST /api/expense/settlements
Authorization: Bearer <token>
{
  "group_id": "<group_id>",
  "from_user": "<user_id>",
  "to_user": "<other_user_id>",
  "amount": 25.00
}
```

**Expected Results:**
- ✅ Response time: <1500ms (optimized in Phase 2.2)
- ✅ Response includes settlement record
- ✅ HTTP Status: 201

**Check Logs:**
```
📧 Queued settlement notification for user@example.com
```

---

### Test 4: Group Invitation

**Objective:** Verify invitation emails are queued

**Steps:**
```bash
POST /api/expense/groups/<group_id>/invite
Authorization: Bearer <token>
{
  "invited_email": "newuser@example.com"
}
```

**Expected Results:**
- ✅ Response time: <300ms
- ✅ Response includes invitation_id and link
- ✅ HTTP Status: 201

**Check Logs:**
```
📧 Invitation email queued for newuser@example.com
```

---

### Test 5: Health Check with Worker Stats

**Objective:** Verify worker monitoring integration

**Steps:**
```bash
GET /api/expense/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-19T...",
  "firebase": { "status": "connected" },
  "redis": { "status": "connected", ... },
  "email_worker": {
    "status": "healthy",
    "queue_size": 0,
    "processed": 15,
    "failed": 0
  },
  ...
}
```

**Expected Results:**
- ✅ `email_worker.status`: "healthy"
- ✅ `email_worker.queue_size`: 0-5 (depends on load)
- ✅ `email_worker.processed`: > 0 (after running tests)
- ✅ `email_worker.failed`: 0 or very low
- ✅ HTTP Status: 200

---

### Test 6: Email Delivery Verification

**Objective:** Verify emails are actually sent (not just queued)

**Prerequisites:** Valid SMTP credentials configured

**Steps:**
1. Perform Test 1 (delete expense)
2. Wait 5-10 seconds
3. Check recipient inbox

**Expected Results:**
- ✅ Email received with subject: "🗑️ Expense deleted in '<group_name>'"
- ✅ Email contains expense details
- ✅ Email formatting is correct

**If Email Not Received:**
Check logs for:
```
✅ Sent expense_deleted email to 1 recipients (total: X)
```

Or error:
```
❌ Email failed after 3 retries: expense_deleted to [...]
```

---

## 🐛 Troubleshooting

### Issue: Delete still slow (>1000ms)

**Possible Causes:**
1. Email worker not started
2. Old threading code still being used
3. Database operation slow

**Debug Steps:**
```bash
# Check health endpoint
GET /api/expense/health

# Look for email_worker section
# If missing or status="error", worker not running
```

**Solution:**
```bash
# Restart backend
cd web/backend
python -m expense_engine.workers.email_worker  # Test worker standalone

# Or restart main app
python run.py
```

---

### Issue: Emails not being sent

**Possible Causes:**
1. SMTP credentials not configured
2. Worker thread crashed
3. Email service disabled

**Debug Steps:**
```bash
# Check logs for:
⚠️ Email service disabled

# Or check environment:
echo $SMTP_USER
echo $SMTP_PASSWORD  # Should be SET
```

**Solution:**
```bash
# Set SMTP credentials in .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourapp.com

# Restart backend
```

---

### Issue: Worker stats show high failed count

**Possible Causes:**
1. Invalid SMTP credentials
2. Network issues
3. Rate limiting from email provider

**Debug Steps:**
```bash
# Check logs for retry attempts:
🔄 Retrying expense_deleted email (attempt 1/3)

# Check final failure:
❌ Email failed after 3 retries: expense_deleted to [...]
```

**Solution:**
1. Verify SMTP credentials
2. Check email provider limits (Gmail: 100/day for free, 500/day for Workspace)
3. Consider using transactional email service (SendGrid, Mailgun)

---

## 📊 Performance Benchmarks

### Target Metrics (Phase 2.1)

| Operation | Target | Acceptance Criteria |
|-----------|--------|---------------------|
| Delete expense | <500ms | ✅ Must be <1000ms |
| Create expense | <300ms | ✅ Must be <500ms |
| Settlement | <1500ms | ⚠️ Optimized in Phase 2.2 |
| Invitation | <300ms | ✅ Must be <500ms |
| Health check | <100ms | ✅ Must be <200ms |

### Email Worker Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Queue processing | <5s per email | Measured in logs |
| Queue size | 0-10 | Check health endpoint |
| Success rate | >95% | (processed - failed) / processed |
| Retry rate | <10% | Emails needing retry / total |

---

## ✅ Sign-off Checklist

Before marking Phase 2.1 complete, verify:

- [ ] Delete expense: <500ms response time
- [ ] Create expense: Non-blocking email
- [ ] Settlement: Non-blocking email
- [ ] Invitation: Non-blocking email
- [ ] Health endpoint shows worker stats
- [ ] Worker stats show processed > 0
- [ ] Worker stats show failed = 0 (or very low)
- [ ] Emails actually delivered to inbox
- [ ] No errors in logs
- [ ] No breaking changes to existing functionality

**When all boxes checked:** Phase 2.1 is production-ready! ✅

---

## 📚 Related Documentation

- `PHASE2.1_EMAIL_WORKER_COMPLETE.md` - Implementation summary
- `WEEK2_ARCHITECTURE_PLAN.md` - Overall Week 2 plan
- `WEEK1_COMPLETION_REPORT.md` - Week 1 baseline metrics
- `workers/email_worker.py` - Worker implementation
- `routes.py` - Updated email calls

---

## 🚀 Next Phase

Once testing is complete and Phase 2.1 is verified:

**Phase 2.2: Member Management & Settlement Optimization**
- Implement member details endpoint
- Optimize settlement validation (1204ms → 500ms)
- Prepare for route modularization

Expected completion: 2-3 hours
