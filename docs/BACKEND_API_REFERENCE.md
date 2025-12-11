# Backend API Reference

Complete reference for the Expense Engine Backend API.

**Base URL:** `/api/expense`

**Authentication:** All endpoints require Firebase JWT authentication via `Authorization: Bearer <token>` header.

---

## Groups API

### Create Group
- **Endpoint:** `POST /api/expense/groups`
- **Description:** Create a new expense group
- **Request Body:**
  ```json
  {
    "name": "Trip to Paris",
    "description": "Summer vacation expenses",
    "currency": "EUR",
    "category": "travel"
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "success": true,
    "group": {
      "group_id": "group123",
      "name": "Trip to Paris",
      "created_by": "user123",
      "members": [...],
      ...
    }
  }
  ```

### Get Group
- **Endpoint:** `GET /api/expense/groups/:gid`
- **Description:** Get group details
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "group": {...}
  }
  ```

### Update Group
- **Endpoint:** `PATCH /api/expense/groups/:gid`
- **Description:** Update group details (admin/owner only)
- **Request Body:**
  ```json
  {
    "name": "Updated name",
    "description": "New description",
    "category": "travel"
  }
  ```
- **Response:** `200 OK`

### Delete Group
- **Endpoint:** `DELETE /api/expense/groups/:gid`
- **Description:** Soft delete group (owner only)
- **Response:** `200 OK`

### Get Group Members
- **Endpoint:** `GET /api/expense/groups/:gid/members`
- **Description:** Get all group members
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "members": [
      {
        "user_id": "user123",
        "display_name": "John Doe",
        "role": "admin",
        "joined_at": "2025-01-01T10:00:00Z"
      }
    ]
  }
  ```

### Add Group Member
- **Endpoint:** `POST /api/expense/groups/:gid/members`
- **Description:** Add member directly (admin only)
- **Request Body:**
  ```json
  {
    "user_id": "user456",
    "role": "member"
  }
  ```
- **Response:** `201 Created`

### Remove Group Member
- **Endpoint:** `DELETE /api/expense/groups/:gid/members/:uid`
- **Description:** Remove member from group (admin or self)
- **Response:** `200 OK`

### Update Member Role
- **Endpoint:** `PATCH /api/expense/groups/:gid/members/:uid/role`
- **Description:** Change member's role (owner only)
- **Request Body:**
  ```json
  {
    "role": "admin"
  }
  ```
- **Response:** `200 OK`

### Get Group Summary
- **Endpoint:** `GET /api/expense/groups/:gid/summary`
- **Description:** Get comprehensive group summary with balances, members, recent expenses, and statistics
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "group": {...},
    "members": [...],
    "balances": [...],
    "recent_expenses": [...],
    "stats": {
      "total_expenses": 42,
      "total_amount": 1500.00,
      "member_count": 5
    }
  }
  ```

---

## Expenses API

### Create Expense
- **Endpoint:** `POST /api/expense/groups/:gid/expenses`
- **Description:** Create new expense
- **Request Body:**
  ```json
  {
    "description": "Dinner at restaurant",
    "amount": 150.00,
    "currency": "USD",
    "paid_by": "user123",
    "split_type": "equal",
    "split_details": [
      {"user_id": "user123", "amount": 50.00},
      {"user_id": "user456", "amount": 50.00},
      {"user_id": "user789", "amount": 50.00}
    ],
    "category": "food",
    "date": "2025-01-15",
    "notes": "Great dinner!",
    "receipt_url": "https://..."
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "success": true,
    "expense": {...},
    "balances": {...}
  }
  ```

### Get Expense
- **Endpoint:** `GET /api/expense/groups/:gid/expenses/:eid`
- **Description:** Get expense details
- **Response:** `200 OK`

### List Expenses
- **Endpoint:** `GET /api/expense/groups/:gid/expenses`
- **Description:** List group expenses with pagination
- **Query Parameters:**
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
  - `category` (optional)
  - `paid_by` (optional)
  - `start_date` (optional, ISO 8601)
  - `end_date` (optional, ISO 8601)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "expenses": [...],
    "page": 1,
    "limit": 20,
    "has_more": true,
    "total": 150
  }
  ```

### Update Expense
- **Endpoint:** `PATCH /api/expense/groups/:gid/expenses/:eid`
- **Description:** Update expense (creator or admin only)
- **Request Body:** (partial update)
  ```json
  {
    "description": "Updated description",
    "amount": 160.00,
    "notes": "Updated notes"
  }
  ```
- **Response:** `200 OK`

### Delete Expense
- **Endpoint:** `DELETE /api/expense/groups/:gid/expenses/:eid`
- **Description:** Soft delete expense (creator or admin only)
- **Response:** `200 OK`

---

## Settlements API

### Create Settlement
- **Endpoint:** `POST /api/expense/groups/:gid/settlements`
- **Description:** Record a payment/settlement
- **Request Body:**
  ```json
  {
    "from_user_id": "user123",
    "to_user_id": "user456",
    "amount": 50.00,
    "currency": "USD",
    "method": "cash",
    "notes": "Settling up",
    "proof_url": "https://..."
  }
  ```
- **Response:** `201 Created`

### Get Settlement
- **Endpoint:** `GET /api/expense/groups/:gid/settlements/:sid`
- **Description:** Get settlement details
- **Response:** `200 OK`

### List Settlements
- **Endpoint:** `GET /api/expense/groups/:gid/settlements`
- **Description:** List group settlements with pagination
- **Query Parameters:**
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
- **Response:** `200 OK`

### Get User Settlements
- **Endpoint:** `GET /api/expense/groups/:gid/settlements/user/:uid`
- **Description:** Get settlements for specific user
- **Query Parameters:** Same as List Settlements
- **Response:** `200 OK`

### Add Payment Proof
- **Endpoint:** `POST /api/expense/groups/:gid/settlements/:sid/proof`
- **Description:** Add payment proof to settlement
- **Request Body:**
  ```json
  {
    "proof_url": "https://...",
    "notes": "Payment receipt"
  }
  ```
- **Response:** `200 OK`

---

## User API

### Get User Groups
- **Endpoint:** `GET /api/expense/user/groups`
- **Description:** Get all groups for current user
- **Query Parameters:**
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "groups": [...],
    "page": 1,
    "limit": 20,
    "has_more": false
  }
  ```

### Get User Balance (in Group)
- **Endpoint:** `GET /api/expense/user/groups/:gid/balance`
- **Description:** Get user's balance in specific group
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "balance": 50.00,
    "currency": "USD",
    "owed_to": [
      {"user_id": "user456", "amount": 30.00, "name": "Jane"}
    ],
    "owes": [
      {"user_id": "user789", "amount": 20.00, "name": "Bob"}
    ]
  }
  ```

### Get All User Balances
- **Endpoint:** `GET /api/expense/user/balances`
- **Description:** Get user's balances across all groups
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "balances": [
      {
        "group_id": "group123",
        "group_name": "Trip to Paris",
        "balance": 50.00,
        "currency": "USD"
      }
    ],
    "total_owed_to_you": 150.00,
    "total_you_owe": 100.00,
    "net_balance": 50.00
  }
  ```

### Get User Invitations
- **Endpoint:** `GET /api/expense/user/invitations`
- **Description:** Get pending invitations for current user
- **Query Parameters:**
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
- **Response:** `200 OK`

### Get User Statistics
- **Endpoint:** `GET /api/expense/user/stats`
- **Description:** Get user statistics
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "stats": {
      "total_groups": 5,
      "total_expenses": 42,
      "total_spent": 1500.00,
      "total_paid": 800.00,
      "pending_invitations": 2,
      "active_settlements": 3
    }
  }
  ```

### Get Recent Activity
- **Endpoint:** `GET /api/expense/user/recent-activity`
- **Description:** Get recent activity feed
- **Query Parameters:**
  - `limit` (default: 10, max: 50)
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "activity": [
      {
        "type": "expense",
        "id": "exp123",
        "group_id": "group456",
        "group_name": "Trip to Paris",
        "description": "Dinner",
        "amount": 50.00,
        "timestamp": "2025-11-24T10:30:00Z"
      }
    ]
  }
  ```

### Search User Expenses
- **Endpoint:** `GET /api/expense/user/search`
- **Description:** Search expenses across all user's groups
- **Query Parameters:**
  - `q` (required) - Search query
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
- **Response:** `200 OK`

---

## Invitations API

### Create Invitation
- **Endpoint:** `POST /api/expense/invitations`
- **Description:** Create new invitation
- **Request Body:**
  ```json
  {
    "group_id": "group123",
    "invited_email": "user@example.com",
    "invited_user_id": "user456",
    "message": "Join our expense group!"
  }
  ```
- **Response:** `201 Created`

### Get Invitation
- **Endpoint:** `GET /api/expense/invitations/:iid`
- **Description:** Get invitation details
- **Response:** `200 OK`

### Get User Invitations
- **Endpoint:** `GET /api/expense/invitations/user`
- **Description:** Get invitations for current user
- **Query Parameters:**
  - `status` (default: "pending", values: "pending"|"accepted"|"declined")
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
- **Response:** `200 OK`

### Get Group Invitations
- **Endpoint:** `GET /api/expense/invitations/group/:gid`
- **Description:** Get invitations for a group
- **Query Parameters:**
  - `status` (optional)
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
- **Response:** `200 OK`

### Accept Invitation
- **Endpoint:** `POST /api/expense/invitations/:iid/accept`
- **Description:** Accept invitation
- **Response:** `200 OK`
  ```json
  {
    "success": true,
    "message": "Invitation accepted successfully",
    "group": {...}
  }
  ```

### Decline Invitation
- **Endpoint:** `POST /api/expense/invitations/:iid/decline`
- **Description:** Decline invitation
- **Request Body:**
  ```json
  {
    "reason": "Optional decline reason"
  }
  ```
- **Response:** `200 OK`

### Revoke Invitation
- **Endpoint:** `POST /api/expense/invitations/:iid/revoke`
- **Description:** Revoke invitation (inviter or admin only)
- **Response:** `200 OK`

### Resend Invitation
- **Endpoint:** `POST /api/expense/invitations/:iid/resend`
- **Description:** Resend invitation (extends expiry)
- **Response:** `200 OK`

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message"
}
```

**Status Codes:**
- `400` - Validation Error (invalid request data)
- `401` - Unauthorized (missing or invalid auth token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `409` - Conflict (duplicate entry)
- `500` - Internal Server Error

---

## Migration Guide: Old → New Endpoints

### OLD (Legacy Splitwise API)
```
GET  /api/splitwise/groups
POST /api/splitwise/group/create
GET  /api/splitwise/group/:id
```

### NEW (Expense Engine API)
```
GET  /api/expense/user/groups
POST /api/expense/groups
GET  /api/expense/groups/:gid
```

**Key Changes:**
1. All routes now under `/api/expense`
2. User-specific data moved to `/api/expense/user/*`
3. Consistent URL structure with resource nesting
4. Standard REST conventions (POST for create, PATCH for update, DELETE for soft delete)
5. Consistent pagination with `page` and `limit` parameters
6. All responses include `success` boolean
7. Group ID parameter is `:gid` not `:id`
8. Expense ID parameter is `:eid`
9. Settlement ID parameter is `:sid`
10. Invitation ID parameter is `:iid`

---

## Pagination

All list endpoints support pagination:

**Request:**
```
GET /api/expense/user/groups?page=2&limit=20
```

**Response:**
```json
{
  "success": true,
  "groups": [...],
  "page": 2,
  "limit": 20,
  "has_more": true
}
```

- `page`: Current page number (1-indexed)
- `limit`: Items per page (default: 20, max: 100)
- `has_more`: Boolean indicating if more pages exist

---

## Authentication

All endpoints require Firebase JWT authentication.

**Header:**
```
Authorization: Bearer <firebase-jwt-token>
```

The `@require_auth` decorator automatically:
1. Validates the JWT token
2. Extracts the user ID
3. Makes it available via `get_current_user_id()`

---

## Common Patterns

### Creating a Group and Adding Members
```javascript
// 1. Create group
const group = await POST('/api/expense/groups', {
  name: 'Trip to Paris',
  description: 'Summer vacation'
});

// 2. Invite members via invitation
await POST('/api/expense/invitations', {
  group_id: group.group_id,
  invited_email: 'friend@example.com',
  message: 'Join us!'
});

// 3. Or add member directly (if you know their user_id)
await POST(`/api/expense/groups/${group.group_id}/members`, {
  user_id: 'user456',
  role: 'member'
});
```

### Creating an Expense
```javascript
const expense = await POST(`/api/expense/groups/${groupId}/expenses`, {
  description: 'Dinner',
  amount: 150.00,
  paid_by: currentUserId,
  split_type: 'equal',
  split_details: [
    { user_id: 'user1', amount: 50.00 },
    { user_id: 'user2', amount: 50.00 },
    { user_id: 'user3', amount: 50.00 }
  ],
  category: 'food',
  date: '2025-01-15'
});
```

### Settling Up
```javascript
// Record a payment
const settlement = await POST(`/api/expense/groups/${groupId}/settlements`, {
  from_user_id: payerId,
  to_user_id: receiverId,
  amount: 50.00,
  method: 'venmo',
  notes: 'Settling restaurant bill'
});

// Add proof later
await POST(`/api/expense/groups/${groupId}/settlements/${settlement.settlement_id}/proof`, {
  proof_url: 'https://receipt-url.com/image.jpg',
  notes: 'Payment confirmation'
});
```

---

## Complete Endpoint List (35 endpoints)

### Groups (9 endpoints)
1. POST /api/expense/groups
2. GET /api/expense/groups/:gid
3. PATCH /api/expense/groups/:gid
4. DELETE /api/expense/groups/:gid
5. GET /api/expense/groups/:gid/members
6. POST /api/expense/groups/:gid/members
7. DELETE /api/expense/groups/:gid/members/:uid
8. PATCH /api/expense/groups/:gid/members/:uid/role
9. GET /api/expense/groups/:gid/summary

### Expenses (5 endpoints)
10. POST /api/expense/groups/:gid/expenses
11. GET /api/expense/groups/:gid/expenses/:eid
12. GET /api/expense/groups/:gid/expenses
13. PATCH /api/expense/groups/:gid/expenses/:eid
14. DELETE /api/expense/groups/:gid/expenses/:eid

### Settlements (5 endpoints)
15. POST /api/expense/groups/:gid/settlements
16. GET /api/expense/groups/:gid/settlements/:sid
17. GET /api/expense/groups/:gid/settlements
18. GET /api/expense/groups/:gid/settlements/user/:uid
19. POST /api/expense/groups/:gid/settlements/:sid/proof

### User (7 endpoints)
20. GET /api/expense/user/groups
21. GET /api/expense/user/groups/:gid/balance
22. GET /api/expense/user/balances
23. GET /api/expense/user/invitations
24. GET /api/expense/user/stats
25. GET /api/expense/user/recent-activity
26. GET /api/expense/user/search

### Invitations (9 endpoints)
27. POST /api/expense/invitations
28. GET /api/expense/invitations/:iid
29. GET /api/expense/invitations/user
30. GET /api/expense/invitations/group/:gid
31. POST /api/expense/invitations/:iid/accept
32. POST /api/expense/invitations/:iid/decline
33. POST /api/expense/invitations/:iid/revoke
34. POST /api/expense/invitations/:iid/resend

---

**Total: 34 RESTful endpoints**

All endpoints follow consistent patterns, use proper HTTP methods, and return standardized JSON responses.
