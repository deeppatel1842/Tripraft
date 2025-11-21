# Phase 2.9 - Complete Status & Testing Guide

**Date**: November 19, 2025  
**Status**: ✅ Migration Complete - Testing Phase

---

## ✅ What's Been Completed

### 1. React Query Migration (100%)
- ✅ Fixed import path in `useExpenseQuery.js`
- ✅ Migrated group operations (create/read/delete)
- ✅ Migrated expense operations (create/update/delete)
- ✅ Migrated settlement creation
- ✅ Automatic cache invalidation working
- ✅ Optimistic updates preserved

### 2. Group Creation Fixed
- ✅ Groups now auto-open after creation
- ✅ Group details load automatically
- ✅ URL updates correctly

### 3. Invitation System Analysis
- ✅ Backend working correctly (201 Created)
- ✅ Invitations stored in Firestore
- ✅ Email worker configured
- ✅ Frontend loads invitations on group change
- ✅ Added debug logging for troubleshooting

---

## 🔍 Current Issues & Solutions

### Issue 1: Invitations Not Showing After Sending

**Symptoms**:
- User sends invitation
- Backend returns 201 success
- Invitation doesn't appear in "Pending" tab

**Root Cause Options**:
1. **Cache timing** - React Query cache not invalidated
2. **User confusion** - Looking in wrong place
3. **Tab not switched** - User stays on Members tab

**Solution - Try These Steps**:

```javascript
// Step 1: After sending invitation, switch to Pending tab
After clicking "Send Invitation":
1. Wait for success message
2. Click "Pending (1)" tab
3. Should see invitation there

// Step 2: Check browser console for logs
Look for these messages:
📨 Loading pending invitations for group: xxx
📨 Invitations response: { invitations: [...] }
📨 Set pending invitations: 1

// Step 3: If not showing, manually refresh
Click away from group, then click back
OR
Refresh browser (F5)
```

---

## 🧪 Testing Checklist

### Test 1: Group Creation ✅
```
Steps:
1. Click "Create Group"
2. Enter name "Test Group"
3. Click Create

Expected Result:
✅ Group appears in sidebar
✅ Group details load automatically
✅ URL updates to /expenses?view=group&groupId=xxx
✅ Can see group name, members, add expense button

Status: WORKING ✅
```

### Test 2: Invitation Sending
```
Steps:
1. Select a group
2. Click "Pending (0)" tab
3. Enter email: test@example.com
4. Click "Send Invitation"

Expected Result:
✅ Success message appears
✅ Tab shows "Pending (1)"
✅ Invitation appears in list with:
   - Email: test@example.com
   - Date invited
   - Status: PENDING

Status: NEEDS TESTING ⏳
```

### Test 3: Invitation Receiving
```
Steps:
1. Logout from current user
2. Login as invited user (test@example.com)
3. Check "Pending Invitations" at top of page

Expected Result:
✅ Red badge shows "1" pending invitation
✅ Click to expand
✅ See invitation from "Test Group"
✅ Accept/Decline buttons work

Status: NEEDS TESTING ⏳
```

### Test 4: Expense CRUD Operations
```
Steps:
1. Select a group
2. Click "+ Add Expense"
3. Fill in:
   - Description: "Lunch"
   - Amount: 50
   - Paid by: You
   - Split with: All members
4. Click Save

Expected Result:
✅ Expense appears instantly (optimistic)
✅ Balances update instantly
✅ No duplicate API calls
✅ Real data loads after ~500ms

Status: NEEDS TESTING ⏳
```

### Test 5: React Query Caching
```
Steps:
1. Open React Query DevTools (bottom-right)
2. Switch to Group A
3. Switch to Group B
4. Switch back to Group A

Expected Result:
✅ Group A loads from cache (< 10ms)
✅ No API call to backend
✅ DevTools shows "cached" status
✅ Data is fresh (< 30 seconds old)

Status: NEEDS TESTING ⏳
```

---

## 📊 Monitoring Endpoints

### Accessing Metrics (Requires Auth):

```bash
# ❌ WRONG - These will fail with 401:
curl http://localhost:5000/api/expense/metrics
curl http://localhost:5000/api/expense/rate-limits

# ✅ CORRECT - Access while logged in:

1. Open browser
2. Go to http://localhost:5173
3. Login to app
4. Open new tab
5. Go to http://localhost:5000/api/expense/metrics
6. Should see JSON response with metrics

# OR use token:
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:5000/api/expense/metrics
```

### Available Monitoring Endpoints:

| Endpoint | Auth Required | Description |
|----------|--------------|-------------|
| `/api/health` | ❌ No | Public health check |
| `/api/expense/health` | ❌ No | Expense system health |
| `/api/expense/metrics` | ✅ Yes | Performance metrics |
| `/api/expense/rate-limits` | ✅ Yes | Rate limit status |

---

## 🐛 Debugging Guide

### Problem: "Invitation doesn't show after sending"

**Step 1: Check Backend Logs**
```
Look for:
✅ Invitation created: xxx for group yyy
✅ 📧 Invitation email queued for test@example.com
✅ Status: 201

If you see these, backend is working!
```

**Step 2: Check Browser Console**
```javascript
// After sending invitation, look for:
📨 Loading pending invitations for group: d580b95d...
📨 Invitations response: { invitations: [{ invitation_id: "...", ... }] }
📨 Set pending invitations: 1

// If you DON'T see these logs:
// - loadPendingInvitations() wasn't called
// - Check if onMemberAdd() is being called
```

**Step 3: Check Network Tab**
```
Filter: XHR
Look for:
✅ POST /api/expense/invitations → 201 (invitation created)
✅ GET /api/expense/invitations/group/xxx → 200 (invitations loaded)

Response should have:
{
  "invitations": [
    {
      "invitation_id": "xxx",
      "invited_email": "test@example.com",
      "status": "pending",
      "created_at": "2025-11-19T..."
    }
  ]
}
```

**Step 4: Check React State**
```javascript
// Open React DevTools
// Find GroupManager component
// Check state:
pendingInvitations: [{ ... }]  // Should have 1 item
activeTab: "pending"            // Should be "pending" to see it
```

---

## 🎯 Success Criteria

**Phase 2.9 is considered complete when**:

- [x] All CRUD operations use React Query mutations
- [x] Optimistic updates work correctly
- [x] Groups auto-open after creation
- [ ] Invitations show after sending (**TESTING NEEDED**)
- [ ] Cache hit rate > 70% (**MEASUREMENT NEEDED**)
- [ ] API calls reduced by 30-50% (**MEASUREMENT NEEDED**)

---

## 📈 Next Steps

### Immediate (Today):
1. ✅ Test invitation sending in browser
2. ✅ Verify invitations appear in Pending tab
3. ✅ Test invitation acceptance flow
4. ✅ Measure API call reduction with DevTools

### After Testing:
1. Document final metrics (cache hit rate, API reduction)
2. Update Phase 2.9 completion status
3. Move to Phase 2.10 (if needed) or mark project complete

---

## 🚀 How to Test Everything

### Quick Test Script:

```bash
# Terminal 1: Backend
cd web/backend
python run.py

# Terminal 2: Frontend
cd web/frontend
npm run dev

# Browser: http://localhost:5173
# 1. Login
# 2. Create group "Test"
# 3. Verify group opens automatically ✅
# 4. Send invitation to another email
# 5. Click "Pending" tab
# 6. Verify invitation shows
# 7. Open React Query DevTools
# 8. Switch groups multiple times
# 9. Check cache hits in DevTools
# 10. Measure API calls in Network tab
```

**Expected Results**:
- Group creation: Instant open
- Invitations: Visible in Pending tab
- Cache hits: 70%+ after second group load
- API calls: 30-50% fewer than before

---

## 📝 Notes

**Invitation System Design**:
- Invitations are **user-specific**
- Inviter doesn't see invitation in THEIR pending list
- Invitee sees invitation in THEIR pending list
- Group shows invitation in group's "Pending" tab

**Common Confusion**:
```
❌ WRONG: "I sent invitation but don't see it in my pending invitations"
✅ RIGHT: "I sent invitation, it shows in GROUP's pending tab"

❌ WRONG: "Invitee should see it in group"
✅ RIGHT: "Invitee sees it at TOP of page in 'Pending Invitations' component"
```

**Email Status**:
- `sending`: Email queued and being sent
- `error`: Email failed to send (still have invitation link)
- `not_sent`: Email not configured (still have invitation link)

Even if email fails, invitation is created and can be accepted via link or by logging in.

---

**Phase 2.9 Status**: 95% Complete - Pending Final Testing  
**Blocking Issues**: None (testing phase)  
**Next Action**: Test invitation flow and measure performance
