# Expense Engine API Reference

## Overview

The Expense Engine provides a complete REST API for managing group expenses, settlements, and invitations. All endpoints require authentication via Firebase JWT tokens.

**Base URL**: `/api/expense`

## Authentication

All endpoints (except OPTIONS preflight) require a valid Firebase JWT token in the Authorization header:

```
Authorization: Bearer <firebase_jwt_token>
```

## Response Format

All responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message"
}
```

Error responses:

```json
{
  "success": false,
  "error": "Error type",
  "message": "Human readable error message"
}
```

---

## Bootstrap Endpoint

### GET /api/expense/bootstrap

Get all data needed to render the dashboard in a single request.

**Response:**
```json
{
  "user": {
    "user_id": "string",
    "email": "string",
    "display_name": "string",
    "photo_url": "string"
  },
  "groups": [
    {
      "group_id": "string",
      "name": "string",
      "member_count": 3,
      "user_balance": 50.00,
      "currency": "USD",
      "last_activity": "2025-01-27T10:00:00Z"
    }
  ],
  "pending_invitations": [
    {
      "invitation_id": "string",
      "group_id": "string",
      "group_name": "string",
      "invited_by_name": "string",
      "expires_at": "2025-02-01T00:00:00Z"
    }
  ],
  "summary": {
    "total_groups": 3,
    "pending_invitations_count": 1,
    "total_owed": 150.00,
    "total_owes": 50.00
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### POST /api/expense/bootstrap/refresh

Force refresh the bootstrap data (bypasses cache).

**Response:** Same as GET /api/expense/bootstrap

---

## Group Endpoints

### POST /api/expense/groups

Create a new expense group.

**Request Body:**
```json
{
  "name": "Trip to Paris",
  "description": "Expenses for our Paris trip",
  "currency": "USD"
}
```

**Response:**
```json
{
  "success": true,
  "group": {
    "group_id": "abc123",
    "name": "Trip to Paris",
    "description": "Expenses for our Paris trip",
    "currency": "USD",
    "created_by": "user_123",
    "members": ["user_123"],
    "is_active": true,
    "created_at": "2025-01-27T10:00:00Z"
  }
}
```

### GET /api/expense/groups/{group_id}

Get group details.

**Response:**
```json
{
  "success": true,
  "group": {
    "group_id": "abc123",
    "name": "Trip to Paris",
    "description": "Expenses for our Paris trip",
    "currency": "USD",
    "created_by": "user_123",
    "members": [
      {
        "user_id": "user_123",
        "display_name": "John Doe",
        "email": "john@example.com",
        "role": "admin"
      }
    ],
    "is_active": true,
    "created_at": "2025-01-27T10:00:00Z",
    "updated_at": "2025-01-27T12:00:00Z"
  }
}
```

### GET /api/expense/groups/{group_id}/full

Get comprehensive group data including expenses, settlements, and balances.

**Response:**
```json
{
  "success": true,
  "group": { ... },
  "members": [ ... ],
  "balances": {
    "user_123": 50.00,
    "user_456": -50.00
  },
  "suggested_settlements": [
    {
      "from_user": "user_456",
      "to_user": "user_123",
      "amount": 50.00
    }
  ],
  "recent_expenses": [ ... ]
}
```

### PATCH /api/expense/groups/{group_id}

Update group details (admin only).

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

### DELETE /api/expense/groups/{group_id}

Delete a group (admin only). Soft deletes the group.

---

## Member Management

### GET /api/expense/groups/{group_id}/members

List all members of a group.

**Response:**
```json
{
  "success": true,
  "members": [
    {
      "user_id": "user_123",
      "display_name": "John Doe",
      "email": "john@example.com",
      "role": "admin",
      "joined_at": "2025-01-27T10:00:00Z"
    }
  ]
}
```

### DELETE /api/expense/groups/{group_id}/members/{user_id}

Remove a member from a group (admin only).

**Response:**
```json
{
  "success": true,
  "message": "Member removed successfully"
}
```

---

## Expense Endpoints

### POST /api/expense/expenses

Create a new expense.

**Request Body:**
```json
{
  "group_id": "abc123",
  "description": "Dinner at restaurant",
  "amount": 100.00,
  "currency": "USD",
  "category": "Food",
  "date": "2025-01-27",
  "paid_by": "user_123",
  "split_type": "EQUAL",
  "splits": [
    {"user_id": "user_123", "amount": 50.00},
    {"user_id": "user_456", "amount": 50.00}
  ]
}
```

**Split Types:**
- `EQUAL` - Split equally among all participants
- `EXACT` - Exact amounts specified per user
- `PERCENTAGE` - Percentage-based split
- `SHARES` - Share-based split (e.g., 2 shares vs 1 share)

**Response:**
```json
{
  "success": true,
  "expense": {
    "expense_id": "exp_123",
    "group_id": "abc123",
    "description": "Dinner at restaurant",
    "amount": 100.00,
    "currency": "USD",
    "category": "Food",
    "date": "2025-01-27",
    "paid_by": "user_123",
    "paid_by_name": "John Doe",
    "split_type": "EQUAL",
    "splits": [...],
    "created_by": "user_123",
    "created_at": "2025-01-27T20:00:00Z"
  },
  "balances": {
    "user_123": 50.00,
    "user_456": -50.00
  }
}
```

### GET /api/expense/expenses/{expense_id}

Get a single expense.

### GET /api/expense/groups/{group_id}/expenses

List expenses for a group with pagination.

**Query Parameters:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response:**
```json
{
  "success": true,
  "expenses": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "has_more": true
  }
}
```

### PUT /api/expense/expenses/{expense_id}

Update an expense (creator only).

**Request Body:** Same as POST /expenses

### DELETE /api/expense/expenses/{expense_id}

Delete an expense (creator only). Reverses balance changes.

---

## Settlement Endpoints

### POST /api/expense/settlements

Record a settlement payment.

**Request Body:**
```json
{
  "group_id": "abc123",
  "from_user": "user_456",
  "to_user": "user_123",
  "amount": 50.00,
  "notes": "Payment via Venmo"
}
```

**Response:**
```json
{
  "success": true,
  "settlement": {
    "settlement_id": "set_123",
    "group_id": "abc123",
    "from_user": "user_456",
    "to_user": "user_123",
    "amount": 50.00,
    "notes": "Payment via Venmo",
    "status": "completed",
    "created_at": "2025-01-27T22:00:00Z"
  },
  "balances": {
    "user_123": 0.00,
    "user_456": 0.00
  }
}
```

### GET /api/expense/settlements/group/{group_id}

List settlements for a group.

**Query Parameters:**
- `page` (default: 1)
- `limit` (default: 20)

---

## Invitation Endpoints

### POST /api/expense/invitations

Create an invitation to join a group.

**Request Body:**
```json
{
  "group_id": "abc123",
  "invited_email": "friend@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "invitation": {
    "invitation_id": "inv_123",
    "group_id": "abc123",
    "group_name": "Trip to Paris",
    "invited_email": "friend@example.com",
    "invited_by": "user_123",
    "status": "pending",
    "expires_at": "2025-02-03T10:00:00Z",
    "created_at": "2025-01-27T10:00:00Z"
  }
}
```

### GET /api/expense/invitations/user

Get current user's pending invitations.

**Query Parameters:**
- `status` (default: "pending") - Filter by status: pending, accepted, declined, expired

### GET /api/expense/invitations/group/{group_id}

Get all invitations for a group (admin only).

**Query Parameters:**
- `include_all` (default: false) - Include all statuses

### POST /api/expense/invitations/{invitation_id}/accept

Accept an invitation.

**Response:**
```json
{
  "success": true,
  "message": "Invitation accepted",
  "group": {
    "group_id": "abc123",
    "name": "Trip to Paris"
  }
}
```

### POST /api/expense/invitations/{invitation_id}/decline

Decline an invitation.

### POST /api/expense/invitations/{invitation_id}/revoke

Revoke an invitation (inviter only).

---

## User Endpoints

### GET /api/expense/user/groups

Get all groups the current user is a member of.

**Query Parameters:**
- `page` (default: 1)
- `limit` (default: 20)

**Response:**
```json
{
  "success": true,
  "groups": [
    {
      "group_id": "abc123",
      "name": "Trip to Paris",
      "member_count": 3,
      "user_balance": 50.00,
      "currency": "USD"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "has_more": false
  }
}
```

---

## Performance Endpoints

### GET /api/expense/performance/stats

Get performance statistics (for debugging/monitoring).

**Response:**
```json
{
  "cache": {
    "hits": 150,
    "misses": 30,
    "hit_rate": 0.833
  },
  "firestore": {
    "reads": 45,
    "writes": 12
  },
  "requests": {
    "total": 200,
    "avg_latency_ms": 125
  }
}
```

### GET /api/expense/performance/cache

Get cache status and statistics.

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid request body or parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 403 | Forbidden - User lacks permission for this action |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 422 | Validation Error - Request body fails validation |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server-side error |

---

## Rate Limiting

API requests are rate-limited per user:
- Default: 100 requests per minute
- Bootstrap: 30 requests per minute
- Write operations: 50 requests per minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time until limit resets (Unix timestamp)

---

## Caching

The API uses Redis caching with the following TTLs:

| Cache Key | TTL | Description |
|-----------|-----|-------------|
| `expense:user_groups:{uid}` | 60s | User's groups list |
| `expense:group_summary:{gid}` | 30s | Group summary data |
| `expense:membership:{gid}:{uid}` | 60s | Membership check |
| `expense:group:{gid}` | 60s | Group details |

Cache is automatically invalidated on:
- Expense create/update/delete
- Settlement create
- Member add/remove
- Group update

---

## Webhook Events (Future)

The following events will be available for webhook subscriptions:

- `expense.created`
- `expense.updated`
- `expense.deleted`
- `settlement.created`
- `member.added`
- `member.removed`
- `invitation.accepted`

---

## SDK Examples

### JavaScript/TypeScript

```javascript
import { ExpenseAPI } from './services/expenseApi';

// Get bootstrap data
const bootstrap = await ExpenseAPI.getBootstrap();

// Create expense
const expense = await ExpenseAPI.createExpense({
  group_id: 'abc123',
  description: 'Dinner',
  amount: 100,
  paid_by: currentUser.uid,
  split_type: 'EQUAL',
  splits: [
    { user_id: 'user1', amount: 50 },
    { user_id: 'user2', amount: 50 }
  ]
});

// Record settlement
const settlement = await ExpenseAPI.createSettlement({
  group_id: 'abc123',
  from_user: 'user2',
  to_user: 'user1',
  amount: 50
});
```

### Python

```python
from expense_engine.services import ExpenseService, SettlementService

# Create expense
expense_service = ExpenseService()
expense = expense_service.create_expense(
    group_id='abc123',
    description='Dinner',
    amount=Decimal('100.00'),
    paid_by='user1',
    split_type='EQUAL',
    splits=[
        {'user_id': 'user1', 'amount': Decimal('50.00')},
        {'user_id': 'user2', 'amount': Decimal('50.00')}
    ]
)

# Create settlement
settlement_service = SettlementService()
settlement = settlement_service.create_settlement(
    group_id='abc123',
    from_user='user2',
    to_user='user1',
    amount=Decimal('50.00')
)
```

---

## Changelog

### v1.0.0 (Phase 7 Complete - 2025-01-27)
- Initial release
- Bootstrap endpoint for dashboard optimization
- Full CRUD for groups, expenses, settlements
- Invitation workflow
- Redis caching with smart invalidation
- Incremental balance calculations

---

*Documentation generated: January 27, 2025*
*Expense Engine Phase 8 - Testing & Documentation*
