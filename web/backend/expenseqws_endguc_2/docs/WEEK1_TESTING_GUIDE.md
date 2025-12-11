# Quick Test Guide - Week 1 Endpoints

## 🚀 Testing Bootstrap Endpoint

### Test 1: Basic Bootstrap Call
```bash
# Get your Firebase token from browser
# Open DevTools → Application → Storage → Session Storage → firebase:authUser
# Copy the "stsTokenManager.accessToken" value

# Test bootstrap endpoint
curl -X GET "http://localhost:5000/api/expense/bootstrap" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

### Expected Response:
```json
{
  "success": true,
  "data": {
    "user": {
      "uid": "...",
      "email": "...",
      "username": "...",
      "display_name": "..."
    },
    "groups": [
      {
        "id": "...",
        "name": "Trip to Bali",
        "member_count": 4,
        "expense_count": 12,
        "your_balance": -250.00
      }
    ],
    "invitations": [],
    "recent_expenses": [],
    "stats": {
      "total_groups": 1,
      "active_groups": 1,
      "pending_invitations": 0,
      "total_expenses": 12
    }
  },
  "performance": {
    "duration_ms": 650,
    "parallel_execution": true
  }
}
```

---

## 🎯 Testing Dashboard Endpoint

### Test 2: Group Dashboard Call
```bash
# Replace GROUP_ID with your actual group ID
# You can get it from the bootstrap response above

curl -X GET "http://localhost:5000/api/expense/groups/YOUR_GROUP_ID/dashboard" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

### Expected Response:
```json
{
  "success": true,
  "data": {
    "group": {
      "id": "...",
      "name": "Trip to Bali",
      "currency": "USD",
      "member_count": 4
    },
    "members": [
      {
        "uid": "...",
        "display_name": "John Doe",
        "role": "admin"
      }
    ],
    "expenses": [
      {
        "expense_id": "...",
        "description": "Hotel",
        "amount": 450.00
      }
    ],
    "balances": [
      {
        "user_id": "...",
        "balance": -125.50,
        "total_paid": 450.00
      }
    ],
    "settlements": [],
    "invitations": [],
    "summary": {
      "total_expenses": 12,
      "total_amount": 2450.00,
      "total_settlements": 0
    }
  },
  "performance": {
    "duration_ms": 950
  }
}
```

---

## 🧪 Testing from Frontend (Browser Console)

### Test 3: From React App
```javascript
// Open browser console on http://localhost:5173
// Get your auth token
const token = localStorage.getItem('your-auth-key');

// Test bootstrap
fetch('http://localhost:5000/api/expense/bootstrap', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log('Bootstrap:', data));

// Test dashboard (replace GROUP_ID)
fetch('http://localhost:5000/api/expense/groups/GROUP_ID/dashboard', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log('Dashboard:', data));
```

---

## ❌ Testing Error Cases

### Test 4: Unauthorized (no token)
```bash
curl -X GET "http://localhost:5000/api/expense/bootstrap"
# Expected: 401 Unauthorized
```

### Test 5: Invalid Group ID
```bash
curl -X GET "http://localhost:5000/api/expense/groups/invalid-id/dashboard" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: 404 Not Found
```

### Test 6: Not a Member
```bash
# Use another user's token for a group they're not in
curl -X GET "http://localhost:5000/api/expense/groups/SOMEONE_ELSES_GROUP/dashboard" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: 403 Forbidden
```

---

## 📊 Performance Validation

### What to Check:
1. ✅ Response time < 1 second (bootstrap)
2. ✅ Response time < 1.5 seconds (dashboard)
3. ✅ Parallel execution logs in backend console
4. ✅ All data fields present
5. ✅ No errors in backend logs

### Backend Console Should Show:
```
🚀 BOOTSTRAP - Loading dashboard data
✅ USER: Fetched successfully
✅ GROUPS: Fetched successfully
✅ INVITATIONS: Fetched successfully
✅ RECENT_EXPENSES: Fetched successfully

📊 STATISTICS:
   Total Groups: 1
   Pending Invitations: 0
   
⚡ Performance: 650ms (parallel execution)
```

---

## 🔍 Debugging

### If bootstrap fails:
1. Check Firebase token is valid
2. Check user exists in database
3. Check backend logs for errors
4. Verify Redis is running

### If dashboard fails:
1. Check group ID is correct
2. Verify user is member of group
3. Check group exists in Firestore
4. Check backend logs for parallel execution errors

---

## ✅ Success Criteria

- [ ] Bootstrap returns 200 status
- [ ] Bootstrap response has all data fields
- [ ] Bootstrap completes in < 1 second
- [ ] Dashboard returns 200 status
- [ ] Dashboard response has all data fields
- [ ] Dashboard completes in < 1.5 seconds
- [ ] Error cases return correct status codes
- [ ] Backend logs show parallel execution
- [ ] No errors in backend console
- [ ] No syntax errors in code

**If all checks pass: Week 1 is SUCCESS! ✅**
