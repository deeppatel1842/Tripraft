# 🔐 Admin API Access Guide

Complete guide to accessing and using TripRaft admin endpoints with security features.

---

## 🚀 Quick Start

### 1. Start the Backend Server

```bash
cd web/backend
python run.py
```

Server will start at: `http://localhost:5001`

### 2. Run the Admin API Test Script

```bash
# Test public endpoints only
python admin_api_guide.py

# Test all endpoints (with authentication)
python admin_api_guide.py --token "your_firebase_token_here"
```

---

## 🔑 Getting Your Firebase Authentication Token

### Method 1: Browser Console (Easiest)

1. **Open your TripRaft frontend**: `http://localhost:3000`
2. **Login** to your account
3. **Press F12** (or Right-click → Inspect)
4. **Go to Console tab**
5. **Paste this code** and press Enter:

```javascript
firebase.auth().currentUser.getIdToken().then(token => {
    console.log('TOKEN:', token);
    navigator.clipboard.writeText(token);
    alert('Token copied to clipboard!');
});
```

6. **Token is copied!** Now use it with API requests

### Method 2: Using Postman/Insomnia

After getting token from Method 1:

1. Create new request
2. Add header: `Authorization: Bearer YOUR_TOKEN_HERE`
3. Make requests to any authenticated endpoint

### Method 3: Using cURL

```bash
TOKEN="your_firebase_token_here"

curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5001/api/expense/user
```

---

## 📋 Available Admin Endpoints

### 🌐 PUBLIC ENDPOINTS (No Authentication)

#### Health Check
```bash
GET /api/expense/health
```

**Response:**
```json
{
  "status": "healthy",
  "email_worker": {
    "status": "active",
    "queue_size": 0,
    "success_rate": 100
  },
  "performance": {
    "cache_hit_rate": 70.5,
    "total_requests": 1234
  }
}
```

#### Expense Categories
```bash
GET /api/expense/categories
```

**Response:**
```json
[
  "Food",
  "Transport",
  "Accommodation",
  "Entertainment",
  "Shopping",
  "Other"
]
```

#### Split Types
```bash
GET /api/expense/split-types
```

**Response:**
```json
[
  "equal",
  "percentage",
  "amount"
]
```

---

### 🔒 AUTHENTICATED ENDPOINTS (Require Token)

#### User Profile
```bash
GET /api/expense/user
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "user": {
    "user_id": "abc123",
    "email": "user@example.com",
    "display_name": "John Doe",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

#### User Groups
```bash
GET /api/expense/groups
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "groups": [
    {
      "group_id": "group123",
      "name": "Trip to Paris",
      "currency": "EUR",
      "members": ["user1", "user2"],
      "total_expenses": 1500.00
    }
  ]
}
```

#### User Invitations
```bash
GET /api/expense/invitations?limit=20&offset=0
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "invitations": [
    {
      "invitation_id": "inv123",
      "group_id": "group456",
      "group_name": "Weekend Trip",
      "invited_by_name": "Jane Doe",
      "status": "pending"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

---

### 📊 PERFORMANCE MONITORING (Require Token)

#### Performance Report
```bash
GET /api/expense/performance/report?date=2025-11-20
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "report": {
    "date": "2025-11-20",
    "api_calls_count": 127,
    "avg_response_time_ms": 245,
    "slowest_endpoint": {
      "endpoint": "/api/expense/invitations",
      "avg_time_ms": 1558
    },
    "endpoints": {
      "/api/expense/groups": {
        "count": 45,
        "avg_time_ms": 156,
        "min_time_ms": 4,
        "max_time_ms": 1840
      }
    }
  }
}
```

#### Slow Operations
```bash
GET /api/expense/performance/slow-operations
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "slow_operations": [
    {
      "endpoint": "/api/expense/invitations",
      "method": "GET",
      "duration_ms": 1558,
      "timestamp": "2025-11-20T15:30:45Z",
      "user_id": "user123"
    }
  ],
  "count": 1
}
```

#### Firestore Costs
```bash
GET /api/expense/performance/costs?date=2025-11-20
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "date": "2025-11-20",
  "costs": {
    "reads": 2547,
    "writes": 345,
    "read_cost_usd": 0.0015,
    "write_cost_usd": 0.0006,
    "total_cost_usd": 0.0021,
    "projection_monthly": 0.063
  }
}
```

---

### 🗑️ CACHE MANAGEMENT (Require Token)

#### Cache Statistics
```bash
GET /api/expense/cache/stats
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "cache_stats": {
    "hit_rate": 70.5,
    "total_hits": 1234,
    "total_misses": 456,
    "total_requests": 1690
  }
}
```

#### Clear Specific Cache
```bash
DELETE /api/expense/cache/<cache_key>
Authorization: Bearer YOUR_TOKEN
```

Example:
```bash
DELETE /api/expense/cache/expense:formatted_balance:group123
```

#### Clear All Caches
```bash
POST /api/expense/cache/clear-all
Authorization: Bearer YOUR_TOKEN
```

---

## 🔒 Security Features

### Rate Limiting

All endpoints are rate-limited to prevent abuse:

- **Default limits**: 200 requests/hour, 50 requests/minute
- **Based on**: User ID (if authenticated) or IP address
- **Response on limit**: 429 Too Many Requests

**Rate limit headers:**
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1732123456
```

### Input Validation

All POST/PUT/DELETE requests are validated:

- ✅ Expense data: amount ($0.01 - $1M), description (max 500 chars)
- ✅ Settlement data: valid user IDs, positive amounts
- ✅ Group data: name (max 100 chars), valid currency code
- ✅ SQL injection prevention
- ✅ XSS attack prevention

### Audit Logging

All sensitive operations are logged:

- 🔒 Expense creation
- 🔒 Expense deletion
- 🔒 Settlement creation
- 🔒 Group modifications

**Audit logs stored in**: Firestore `audit_logs` collection

**Log format:**
```json
{
  "timestamp": "2025-11-20T15:30:45Z",
  "action": "create_expense",
  "resource_type": "expense",
  "resource_id": "exp123",
  "user_id": "user123",
  "status": "success",
  "details": {
    "group_id": "group456",
    "amount": 50.00,
    "currency": "USD"
  },
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

---

## ⚠️ Token Expiration

**Firebase tokens expire after 1 hour.**

If you see this error:
```json
{
  "error": "Authentication required",
  "message": "Please log in to access this resource"
}
```

**Solution**: Get a new token using the Browser Console method above.

---

## 🧪 Testing Examples

### Test Health Endpoint
```bash
curl http://localhost:5001/api/expense/health
```

### Test Authenticated Endpoint
```bash
TOKEN="your_token_here"
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5001/api/expense/user
```

### Test Performance Report
```bash
TOKEN="your_token_here"
DATE=$(date +%Y-%m-%d)
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:5001/api/expense/performance/report?date=$DATE"
```

### Create Expense (with validation)
```bash
TOKEN="your_token_here"
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "description": "Lunch",
       "amount": 25.50,
       "category": "Food",
       "group_id": "group123",
       "paid_by": "user123",
       "splits": [
         {"user_id": "user123", "amount": 12.75},
         {"user_id": "user456", "amount": 12.75}
       ]
     }' \
     http://localhost:5001/api/expense/expenses
```

---

## 📚 Additional Resources

- **API Routes Viewer**: `http://localhost:5001/api/routes` (HTML UI)
- **Full Backend Docs**: `docs/QUICK_START_BACKEND.md`
- **Performance Guide**: `docs/PHASE_4_REDIS_CACHING.md`
- **Expense Engine Analysis**: `docs/expense/EXPENSE_ENGINE_ANALYSIS_AND_PLAN.md`

---

## 🆘 Troubleshooting

### Problem: 401 Unauthorized
**Solution**: Token expired. Get new token from browser console.

### Problem: 429 Too Many Requests
**Solution**: You've hit the rate limit. Wait 1 minute and try again.

### Problem: 400 Validation Failed
**Solution**: Check request body format. Ensure all required fields are present and valid.

### Problem: Server not responding
**Solution**: 
1. Check server is running: `curl http://localhost:5001/health`
2. Check Redis is running: `redis-cli ping` (should return "PONG")
3. Check logs in terminal where server is running

---

## 🎯 Quick Command Reference

```bash
# Get token from browser console
firebase.auth().currentUser.getIdToken().then(t => console.log(t))

# Test public health
curl http://localhost:5001/api/expense/health

# Test authenticated user profile
curl -H "Authorization: Bearer TOKEN" http://localhost:5001/api/expense/user

# Get performance report
curl -H "Authorization: Bearer TOKEN" \
     "http://localhost:5001/api/expense/performance/report?date=$(date +%Y-%m-%d)"

# Run admin test script
python admin_api_guide.py --token "TOKEN"
```

---

**Last Updated**: November 20, 2025  
**Version**: Week 4 Security Implementation  
**Status**: ✅ All admin endpoints operational with security features
