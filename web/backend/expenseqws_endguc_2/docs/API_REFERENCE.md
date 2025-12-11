# 📚 Complete API Reference - Expense Engine

**Version:** 1.0.0  
**Base URL:** `https://your-domain.com/api/expense`  
**Authentication:** Firebase JWT (Bearer token)

---

## 📋 Table of Contents

1. [User Management APIs](#user-management-apis) (4 endpoints)
2. [Group Management APIs](#group-management-apis) (9 endpoints)
3. [Invitation System APIs](#invitation-system-apis) (6 endpoints)
4. [Expense Management APIs](#expense-management-apis) (7 endpoints)
5. [Settlement & Balance APIs](#settlement--balance-apis) (5 endpoints)
6. [Admin & Monitoring APIs](#admin--monitoring-apis) (9 endpoints)
7. [Error Codes Reference](#error-codes-reference)
8. [Rate Limiting](#rate-limiting)
9. [Performance Timing](#performance-timing)

---

## 🔐 Authentication

All endpoints (except public ones) require Firebase authentication:

```http
Authorization: Bearer <FIREBASE_JWT_TOKEN>
```

**Getting a token:**
```javascript
// Frontend (Firebase SDK)
const idToken = await firebase.auth().currentUser.getIdToken();

// Then include in requests
headers: {
  'Authorization': `Bearer ${idToken}`,
  'Content-Type': 'application/json'
}
```

---

## 1️⃣ User Management APIs

### 1.1 Create User Profile

**Endpoint:** `POST /api/expense/user/profile`  
**Auth:** Required  
**Rate Limit:** 10 requests/minute

**Purpose:** Create or initialize user profile in expense system

**Request Body:**
```json
{
  "display_name": "John Doe",
  "email": "john@example.com",
  "username": "johndoe" // Optional, auto-generated if not provided
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "uid": "firebase-user-id-123",
    "display_name": "John Doe",
    "email": "john@example.com",
    "username": "johndoe",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  },
  "timestamp": "2025-01-15T10:30:00.123Z"
}
```

**Timing:**
- Cold start: ~150ms
- Cached: N/A (profile creation, no cache)

**Error Cases:**
- 400: Missing required fields
- 409: Username already taken
- 500: Firebase write error

---

### 1.2 Get User Profile

**Endpoint:** `GET /api/expense/user/profile`  
**Auth:** Required  
**Rate Limit:** 100 requests/minute

**Purpose:** Retrieve authenticated user's profile

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "uid": "firebase-user-id-123",
    "display_name": "John Doe",
    "email": "john@example.com",
    "username": "johndoe",
    "groups_count": 5,
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

**Timing:**
- Cold start: ~80ms
- Cached (1 hour TTL): ~2ms ⚡

**Caching:**
- Cache key: `user_profile:USER_ID`
- TTL: 3600 seconds (1 hour)
- Invalidated on: Profile update

---

### 1.3 Update User Profile

**Endpoint:** `PUT /api/expense/user/profile`  
**Auth:** Required  
**Rate Limit:** 20 requests/minute

**Request Body:**
```json
{
  "display_name": "John Smith", // Optional
  "username": "johnsmith", // Optional
  "avatar_url": "https://example.com/avatar.jpg" // Optional
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "uid": "firebase-user-id-123",
    "display_name": "John Smith",
    "username": "johnsmith",
    "updated_at": "2025-01-15T11:00:00Z"
  },
  "cache_invalidated": true
}
```

**Timing:** ~100ms (includes cache invalidation)

**Side Effects:**
- Invalidates: `user_profile:USER_ID`
- Invalidates: `display_name:USER_ID` (used in group member lists)
- Propagates to all groups user is member of (display name update)

---

### 1.4 Search Users

**Endpoint:** `GET /api/expense/user/search?q={query}`  
**Auth:** Required  
**Rate Limit:** 60 requests/minute

**Purpose:** Search for users by username or display name (for inviting to groups)

**Query Parameters:**
- `q` (required): Search query (min 2 characters)
- `limit` (optional): Max results (default: 10, max: 50)

**Example:** `GET /api/expense/user/search?q=john&limit=5`

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "uid": "user-123",
      "username": "johndoe",
      "display_name": "John Doe",
      "avatar_url": null
    },
    {
      "uid": "user-456",
      "username": "john_smith",
      "display_name": "John Smith",
      "avatar_url": "https://example.com/avatar2.jpg"
    }
  ],
  "count": 2
}
```

**Timing:**
- First search: ~120ms (Firestore query)
- Same query within 5 min: ~3ms (cached)

**Implementation Notes:**
- Search is case-insensitive
- Searches both username and display_name fields
- Results ordered by relevance (exact match first)

---

## 2️⃣ Group Management APIs

### 2.1 Create Group

**Endpoint:** `POST /api/expense/groups`  
**Auth:** Required  
**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "name": "Apartment Roommates",
  "description": "Shared expenses for apt 5B", // Optional
  "category": "HOME", // Optional: HOME, TRIP, EVENT, OTHER
  "currency": "USD" // Optional, default: USD
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "group_id": "group-abc123",
    "name": "Apartment Roommates",
    "description": "Shared expenses for apt 5B",
    "category": "HOME",
    "currency": "USD",
    "created_by": "user-123",
    "created_at": "2025-01-15T12:00:00Z",
    "members": [
      {
        "uid": "user-123",
        "display_name": "John Doe",
        "role": "owner",
        "joined_at": "2025-01-15T12:00:00Z"
      }
    ],
    "member_count": 1
  }
}
```

**Timing:** ~200ms (Firestore write + initial balance doc)

**Side Effects:**
- Creates group document in Firestore
- Creates empty balance document for group
- Adds creator as owner with full permissions
- Invalidates user's groups cache

---

### 2.2 Get User's Groups

**Endpoint:** `GET /api/expense/groups?mode={summary|full}`  
**Auth:** Required  
**Rate Limit:** 100 requests/minute

**Query Parameters:**
- `mode` (optional): `summary` (default) or `full`
  - `summary`: Group ID, name, member count only (ultra-fast)
  - `full`: Includes members, recent expenses, balance summary

**Example:** `GET /api/expense/groups?mode=summary`

**Response - Summary Mode (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "group_id": "group-abc123",
      "name": "Apartment Roommates",
      "member_count": 4,
      "your_balance": -45.50, // What you owe
      "currency": "USD",
      "last_activity": "2025-01-15T14:30:00Z"
    },
    {
      "group_id": "group-xyz789",
      "name": "Europe Trip 2025",
      "member_count": 6,
      "your_balance": 120.75, // What others owe you
      "currency": "EUR",
      "last_activity": "2025-01-14T10:15:00Z"
    }
  ],
  "count": 2
}
```

**Response - Full Mode (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "group_id": "group-abc123",
      "name": "Apartment Roommates",
      "description": "Shared expenses for apt 5B",
      "currency": "USD",
      "created_at": "2025-01-01T00:00:00Z",
      "members": [
        {
          "uid": "user-123",
          "display_name": "John Doe",
          "role": "owner"
        },
        {
          "uid": "user-456",
          "display_name": "Jane Smith",
          "role": "member"
        }
      ],
      "member_count": 4,
      "recent_expenses": [
        {
          "expense_id": "exp-111",
          "description": "Groceries",
          "amount": 85.50,
          "date": "2025-01-15T12:00:00Z",
          "paid_by": "user-123"
        }
      ],
      "your_balance": -45.50,
      "total_expenses": 1250.75
    }
  ],
  "count": 2
}
```

**Timing:**
- Summary mode (cached): ~5ms ⚡
- Summary mode (cold): ~150ms
- Full mode (cached): ~15ms
- Full mode (cold): ~400ms

**Caching:**
- Summary: `user_groups:USER_ID_summary` (TTL: 30 min)
- Full: `user_groups:USER_ID` (TTL: 30 min)
- Invalidated on: Group join/leave, group update, expense created

**Performance Notes:**
- Summary mode recommended for dashboard/list views
- Full mode recommended when user clicks into specific group
- Pagination not needed (users typically in <20 groups)

---

### 2.3 Get Group Full Details

**Endpoint:** `GET /api/expense/groups/{group_id}/full`  
**Auth:** Required (must be group member)  
**Rate Limit:** 100 requests/minute

**Purpose:** Single optimized endpoint to fetch ALL group data at once

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "group_id": "group-abc123",
    "name": "Apartment Roommates",
    "description": "Shared expenses for apt 5B",
    "currency": "USD",
    "created_by": "user-123",
    "created_at": "2025-01-01T00:00:00Z",
    
    "members": [
      {
        "uid": "user-123",
        "display_name": "John Doe",
        "email": "john@example.com",
        "role": "owner",
        "balance": -45.50,
        "joined_at": "2025-01-01T00:00:00Z"
      },
      {
        "uid": "user-456",
        "display_name": "Jane Smith",
        "role": "member",
        "balance": 120.30
      }
    ],
    
    "expenses": [
      {
        "expense_id": "exp-111",
        "description": "Groceries",
        "amount": 85.50,
        "currency": "USD",
        "category": "FOOD",
        "paid_by": {
          "uid": "user-123",
          "display_name": "John Doe"
        },
        "split_type": "EQUAL",
        "splits": [
          {"uid": "user-123", "amount": 28.50},
          {"uid": "user-456", "amount": 28.50},
          {"uid": "user-789", "amount": 28.50}
        ],
        "created_at": "2025-01-15T12:00:00Z"
      }
    ],
    
    "balances": {
      "simplified_debts": [
        {
          "from_uid": "user-123",
          "from_name": "John Doe",
          "to_uid": "user-456",
          "to_name": "Jane Smith",
          "amount": 45.50
        }
      ],
      "total_expenses": 1250.75,
      "settled_amount": 500.00
    },
    
    "statistics": {
      "total_expenses": 25,
      "total_amount": 1250.75,
      "member_count": 4,
      "active_debts": 2
    }
  }
}
```

**Timing:**
- Cached: ~4ms ⚡ (entire response cached)
- Cold start: ~180ms (optimized batch fetching)

**Caching:**
- Cache key: `group_full:GROUP_ID`
- TTL: 1800 seconds (30 minutes)
- Invalidated on: Any group change (expense added, member joined, etc.)

**Optimization Details:**
- Single Firestore transaction fetches: group doc, members, expenses (last 50), balance doc
- Display names fetched from Redis in batch (1 MGET call)
- Result cached as complete JSON response

---

### 2.4 Update Group

**Endpoint:** `PUT /api/expense/groups/{group_id}`  
**Auth:** Required (owner/admin only)  
**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "name": "New Group Name", // Optional
  "description": "Updated description", // Optional
  "category": "TRIP" // Optional
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "group_id": "group-abc123",
    "name": "New Group Name",
    "description": "Updated description",
    "category": "TRIP",
    "updated_at": "2025-01-15T15:00:00Z"
  },
  "cache_invalidated": ["group_full", "user_groups"]
}
```

**Timing:** ~120ms

**Permissions:**
- Only group owner or admin can update
- 403 if user is regular member

---

### 2.5 Delete Group

**Endpoint:** `DELETE /api/expense/groups/{group_id}`  
**Auth:** Required (owner only)  
**Rate Limit:** 10 requests/minute

**Purpose:** Permanently delete group and all associated data

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Group deleted successfully",
  "deleted": {
    "group_id": "group-abc123",
    "expenses_deleted": 25,
    "settlements_deleted": 8,
    "members_count": 4
  }
}
```

**Timing:** ~500ms (deletes multiple documents + cache invalidation)

**Side Effects:**
- Deletes group document
- Deletes all expenses in group
- Deletes all settlements
- Deletes balance document
- Invalidates cache for ALL members:
  - `user_groups:MEMBER_ID`
  - `user_groups:MEMBER_ID_summary`
  - `group_full:GROUP_ID`

**Permissions:**
- Only group owner can delete
- 403 if user is not owner
- 400 if group has unsettled balances (must settle first)

---

### 2.6 Get Group Members

**Endpoint:** `GET /api/expense/groups/{group_id}/members`  
**Auth:** Required (must be group member)  
**Rate Limit:** 100 requests/minute

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "uid": "user-123",
      "display_name": "John Doe",
      "email": "john@example.com",
      "role": "owner",
      "balance": -45.50,
      "joined_at": "2025-01-01T00:00:00Z"
    },
    {
      "uid": "user-456",
      "display_name": "Jane Smith",
      "role": "member",
      "balance": 120.30,
      "joined_at": "2025-01-05T10:30:00Z"
    }
  ],
  "count": 2
}
```

**Timing:**
- Cached: ~3ms
- Cold: ~100ms

---

### 2.7 Get Member Details

**Endpoint:** `GET /api/expense/groups/{group_id}/members/{user_id}`  
**Auth:** Required (must be group member)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "uid": "user-123",
    "display_name": "John Doe",
    "email": "john@example.com",
    "role": "owner",
    "balance": -45.50,
    "expenses_paid": 12,
    "expenses_involved": 25,
    "total_paid": 850.75,
    "total_share": 896.25,
    "joined_at": "2025-01-01T00:00:00Z"
  }
}
```

**Timing:** ~50ms

---

### 2.8 Remove Member

**Endpoint:** `DELETE /api/expense/groups/{group_id}/members/{user_id}`  
**Auth:** Required (owner/admin only, or removing self)  
**Rate Limit:** 20 requests/minute

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Member removed from group",
  "removed_user": "user-456",
  "cache_invalidated": true
}
```

**Timing:** ~150ms

**Validation:**
- Cannot remove if user has unsettled balance (must settle first)
- Owner can remove any member
- Admin can remove regular members
- Members can only remove themselves
- Cannot remove last member (must delete group instead)

---

### 2.9 Leave Group

**Endpoint:** `POST /api/expense/groups/{group_id}/leave`  
**Auth:** Required  
**Rate Limit:** 20 requests/minute

**Purpose:** Leave a group you're a member of

**Response (200 OK):**
```json
{
  "success": true,
  "message": "You have left the group",
  "group_id": "group-abc123"
}
```

**Timing:** ~150ms

**Validation:**
- Cannot leave if you have unsettled balance
- Owner cannot leave (must transfer ownership first)
- Automatically settles your balance if it's $0.00

---

## 3️⃣ Invitation System APIs

### 3.1 Send Invitation

**Endpoint:** `POST /api/expense/invitations`  
**Auth:** Required  
**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "group_id": "group-abc123",
  "invited_email": "friend@example.com", // Optional if invited_uid provided
  "invited_uid": "user-456", // Optional if invited_email provided
  "role": "member", // Optional, default: "member" (can be "admin")
  "message": "Join our apartment expenses group!" // Optional
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "invitation_id": "inv-xyz789",
    "group_id": "group-abc123",
    "group_name": "Apartment Roommates",
    "invited_by": {
      "uid": "user-123",
      "display_name": "John Doe"
    },
    "invited_email": "friend@example.com",
    "status": "pending",
    "created_at": "2025-01-15T16:00:00Z",
    "expires_at": "2025-01-22T16:00:00Z", // 7 days
    "share_link": "https://app.com/invite/inv-xyz789"
  },
  "email_sent": true
}
```

**Timing:** ~250ms (includes email sending)

**Side Effects:**
- Creates invitation document
- Sends email notification (if email provided)
- Invalidates invitations cache for invited user

**Validation:**
- Must be group member to invite
- Cannot invite existing group members
- Cannot invite if group has max members (limit: 50)
- Email or UID required (at least one)

---

### 3.2 Get User's Invitations

**Endpoint:** `GET /api/expense/invitations`  
**Auth:** Required  
**Rate Limit:** 100 requests/minute

**Query Parameters:**
- `status` (optional): Filter by `pending`, `accepted`, `rejected`
- `limit` (optional): Default 20, max 100
- `offset` (optional): For pagination

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "invitation_id": "inv-xyz789",
      "group": {
        "group_id": "group-abc123",
        "name": "Apartment Roommates",
        "member_count": 4
      },
      "invited_by": {
        "uid": "user-123",
        "display_name": "John Doe"
      },
      "status": "pending",
      "role": "member",
      "created_at": "2025-01-15T16:00:00Z",
      "expires_at": "2025-01-22T16:00:00Z"
    }
  ],
  "count": 1,
  "total": 1,
  "has_more": false
}
```

**Timing:**
- Cached: ~3ms ⚡
- Cold: ~150ms

**Caching:**
- Cache key: `invitations:enriched:USER_ID:limit_X:offset_Y`
- TTL: 600 seconds (10 minutes)
- Invalidated on: New invitation, status change

---

### 3.3 Get Group Invitations

**Endpoint:** `GET /api/expense/invitations/group/{group_id}`  
**Auth:** Required (must be group member)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "invitation_id": "inv-xyz789",
      "invited_email": "friend@example.com",
      "invited_by": "John Doe",
      "status": "pending",
      "created_at": "2025-01-15T16:00:00Z"
    }
  ],
  "count": 1
}
```

**Timing:** ~80ms

---

### 3.4 Get Invitation Details (Public)

**Endpoint:** `GET /api/expense/invitations/{invitation_id}/details`  
**Auth:** NOT required (public endpoint for share links)

**Purpose:** Allow users to view invitation before accepting (public share link)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "invitation_id": "inv-xyz789",
    "group": {
      "name": "Apartment Roommates",
      "member_count": 4,
      "currency": "USD"
    },
    "invited_by": {
      "display_name": "John Doe"
    },
    "status": "pending",
    "expires_at": "2025-01-22T16:00:00Z",
    "is_expired": false
  }
}
```

**Timing:** ~50ms

---

### 3.5 Accept Invitation

**Endpoint:** `POST /api/expense/invitations/{invitation_id}/accept`  
**Auth:** Required  
**Rate Limit:** 30 requests/minute

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Invitation accepted successfully",
  "data": {
    "group_id": "group-abc123",
    "group_name": "Apartment Roommates",
    "your_role": "member"
  },
  "cache_invalidated": true
}
```

**Timing:** ~200ms

**Side Effects:**
- Updates invitation status to "accepted"
- Adds user to group members
- Creates initial balance entry ($0.00)
- Invalidates caches:
  - User's invitation cache (wildcard deletion for all pagination variants)
  - User's groups cache
  - Group members cache
  - Group full cache

**Validation:**
- Invitation must be pending
- Invitation must not be expired
- User cannot accept if already in group
- User must be authenticated as the invited user

---

### 3.6 Reject Invitation

**Endpoint:** `POST /api/expense/invitations/{invitation_id}/reject`  
**Auth:** Required

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Invitation rejected"
}
```

**Timing:** ~80ms

---

## 4️⃣ Expense Management APIs

### 4.1 Create Expense

**Endpoint:** `POST /api/expense/expenses`  
**Auth:** Required  
**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "group_id": "group-abc123", // Optional for personal expenses
  "description": "Dinner at restaurant",
  "amount": 120.50,
  "currency": "USD",
  "category": "FOOD", // FOOD, TRANSPORT, ENTERTAINMENT, UTILITIES, OTHER
  "paid_by_uid": "user-123",
  "split_type": "EQUAL", // EQUAL, PERCENTAGE, CUSTOM, SHARES
  "date": "2025-01-15T19:00:00Z", // Optional, defaults to now
  "notes": "Pizza place downtown", // Optional
  "image_url": "https://example.com/receipt.jpg", // Optional
  
  // Split details (required)
  "splits": [
    {"uid": "user-123", "amount": 40.17},
    {"uid": "user-456", "amount": 40.17},
    {"uid": "user-789", "amount": 40.16}
  ],
  
  // Optional: Idempotency key to prevent duplicates
  "idempotency_key": "expense-creation-uuid-12345"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "expense_id": "exp-111",
    "group_id": "group-abc123",
    "description": "Dinner at restaurant",
    "amount": 120.50,
    "currency": "USD",
    "category": "FOOD",
    "paid_by": {
      "uid": "user-123",
      "display_name": "John Doe"
    },
    "split_type": "EQUAL",
    "splits": [
      {
        "uid": "user-123",
        "display_name": "John Doe",
        "amount": 40.17,
        "net_effect": 80.33 // They paid $120.50, owe $40.17, net +$80.33
      },
      {
        "uid": "user-456",
        "display_name": "Jane Smith",
        "amount": 40.17,
        "net_effect": -40.17 // They owe $40.17
      }
    ],
    "created_at": "2025-01-15T19:00:00Z",
    "created_by": "user-123"
  },
  "balances_updated": true,
  "notifications_sent": 2
}
```

**Timing:** ~200ms (includes balance updates + notifications)

**Side Effects:**
1. Creates expense document in Firestore
2. **Updates balances incrementally** (±$X.XX) - NO full recalculation!
3. Invalidates caches:
   - Group expenses cache
   - Group balance cache
   - User groups cache (all members)
4. Sends email notifications to all split participants (async)

**Validation:**
- `paid_by_uid` must be group member
- All split `uid`s must be group members
- Sum of splits must equal `amount` (within $0.01 tolerance)
- Amount must be > 0
- Splits must have at least 2 participants for group expenses

**Idempotency:**
- If `idempotency_key` provided, duplicate submissions within 24 hours return existing expense
- Prevents accidental double-charges on network retries

---

### 4.2 Get Expense Details

**Endpoint:** `GET /api/expense/expenses/{expense_id}`  
**Auth:** Required (must be group member or expense participant)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "expense_id": "exp-111",
    "group_id": "group-abc123",
    "group_name": "Apartment Roommates",
    "description": "Dinner at restaurant",
    "amount": 120.50,
    "currency": "USD",
    "category": "FOOD",
    "paid_by": {
      "uid": "user-123",
      "display_name": "John Doe"
    },
    "split_type": "EQUAL",
    "splits": [
      {"uid": "user-123", "display_name": "John Doe", "amount": 40.17},
      {"uid": "user-456", "display_name": "Jane Smith", "amount": 40.17},
      {"uid": "user-789", "display_name": "Bob Johnson", "amount": 40.16}
    ],
    "date": "2025-01-15T19:00:00Z",
    "created_at": "2025-01-15T19:05:00Z",
    "created_by": "user-123",
    "notes": "Pizza place downtown",
    "image_url": "https://example.com/receipt.jpg"
  }
}
```

**Timing:** ~60ms

---

### 4.3 Update Expense

**Endpoint:** `PUT /api/expense/expenses/{expense_id}`  
**Auth:** Required (must be expense creator or group admin)

**Request Body:**
```json
{
  "description": "Updated description", // Optional
  "amount": 125.00, // Optional (triggers balance recalculation)
  "category": "ENTERTAINMENT", // Optional
  "splits": [ // Optional (if amount changed, splits required)
    {"uid": "user-123", "amount": 41.67},
    {"uid": "user-456", "amount": 41.67},
    {"uid": "user-789", "amount": 41.66}
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "expense_id": "exp-111",
    "description": "Updated description",
    "amount": 125.00,
    "updated_at": "2025-01-15T20:00:00Z"
  },
  "balance_adjustment": {
    "previous_total": 120.50,
    "new_total": 125.00,
    "difference": 4.50
  }
}
```

**Timing:** ~250ms (includes balance adjustment)

**Side Effects:**
- Updates expense document
- **Adjusts balances incrementally** (difference between old and new amounts)
- Invalidates expense and balance caches
- Sends notification to group members

---

### 4.4 Delete Expense

**Endpoint:** `DELETE /api/expense/expenses/{expense_id}`  
**Auth:** Required (must be expense creator or group admin)  
**Rate Limit:** 20 requests/minute

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Expense deleted successfully",
  "expense_id": "exp-111",
  "balance_reverted": true
}
```

**Timing:** ~200ms

**Side Effects:**
- Deletes expense document
- **Reverts balance changes** (subtracts expense from balances)
- Invalidates all related caches
- Logs deletion in audit trail

---

### 4.5 Get All User Expenses

**Endpoint:** `GET /api/expense/expenses/user`  
**Auth:** Required

**Query Parameters:**
- `limit` (optional): Default 50, max 200
- `offset` (optional): For pagination
- `group_id` (optional): Filter by specific group
- `from_date` (optional): ISO 8601 date
- `to_date` (optional): ISO 8601 date

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "expense_id": "exp-111",
      "description": "Dinner at restaurant",
      "amount": 120.50,
      "your_share": 40.17,
      "paid_by_you": true,
      "group_name": "Apartment Roommates",
      "date": "2025-01-15T19:00:00Z"
    }
  ],
  "count": 1,
  "total": 150,
  "has_more": true
}
```

**Timing:** ~120ms

---

### 4.6 Get Group Expenses

**Endpoint:** `GET /api/expense/expenses/group/{group_id}`  
**Auth:** Required (must be group member)

**Query Parameters:**
- `limit`: Default 50, max 200
- `offset`: For pagination
- `from_date`, `to_date`: Date filters
- `category`: Filter by category
- `paid_by`: Filter by who paid

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "expense_id": "exp-111",
      "description": "Dinner at restaurant",
      "amount": 120.50,
      "currency": "USD",
      "category": "FOOD",
      "paid_by": {
        "uid": "user-123",
        "display_name": "John Doe"
      },
      "split_count": 3,
      "date": "2025-01-15T19:00:00Z"
    }
  ],
  "count": 1,
  "total": 25,
  "summary": {
    "total_amount": 1250.75,
    "your_total_paid": 450.00,
    "your_total_share": 495.50
  }
}
```

**Timing:**
- Cached: ~10ms
- Cold: ~300ms (depends on expense count)

---

### 4.7 Get Personal Expenses Only

**Endpoint:** `GET /api/expense/expenses/personal`  
**Auth:** Required

**Purpose:** Get expenses not associated with any group (personal tracking)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "expense_id": "exp-personal-1",
      "description": "Coffee",
      "amount": 5.50,
      "category": "FOOD",
      "date": "2025-01-15T08:00:00Z"
    }
  ],
  "count": 1
}
```

**Timing:** ~80ms

---

## 5️⃣ Settlement & Balance APIs

### 5.1 Create Settlement

**Endpoint:** `POST /api/expense/settlements`  
**Auth:** Required  
**Rate Limit:** 30 requests/minute

**Purpose:** Record a payment between members

**Request Body:**
```json
{
  "group_id": "group-abc123",
  "from_uid": "user-456", // Who is paying
  "to_uid": "user-123", // Who is receiving
  "amount": 45.50,
  "currency": "USD",
  "notes": "Venmo payment", // Optional
  "payment_method": "VENMO", // Optional: VENMO, CASH, BANK_TRANSFER, etc.
  "payment_date": "2025-01-15T20:00:00Z" // Optional, defaults to now
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "settlement_id": "settle-789",
    "group_id": "group-abc123",
    "from_user": {
      "uid": "user-456",
      "display_name": "Jane Smith"
    },
    "to_user": {
      "uid": "user-123",
      "display_name": "John Doe"
    },
    "amount": 45.50,
    "currency": "USD",
    "payment_method": "VENMO",
    "notes": "Venmo payment",
    "payment_date": "2025-01-15T20:00:00Z",
    "created_at": "2025-01-15T20:01:00Z"
  },
  "balance_updated": {
    "user_456_new_balance": 0.00,
    "user_123_new_balance": 0.00
  }
}
```

**Timing:** ~180ms (includes balance update)

**Side Effects:**
- Creates settlement document
- **Updates balances incrementally** (from_user +amount, to_user -amount)
- Invalidates balance and group caches
- Sends notifications to both parties

**Validation:**
- Both users must be group members
- Amount must be > 0
- Cannot create settlement if no debt exists between users
- Optional: Validate amount doesn't exceed existing debt (warning only)

---

### 5.2 Get Group Settlements

**Endpoint:** `GET /api/expense/settlements/group/{group_id}`  
**Auth:** Required (must be group member)

**Query Parameters:**
- `limit`: Default 50, max 200
- `offset`: For pagination

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "settlement_id": "settle-789",
      "from_user": {
        "uid": "user-456",
        "display_name": "Jane Smith"
      },
      "to_user": {
        "uid": "user-123",
        "display_name": "John Doe"
      },
      "amount": 45.50,
      "currency": "USD",
      "payment_method": "VENMO",
      "payment_date": "2025-01-15T20:00:00Z",
      "created_at": "2025-01-15T20:01:00Z"
    }
  ],
  "count": 1,
  "total": 8,
  "summary": {
    "total_settled": 500.00,
    "settlement_count": 8
  }
}
```

**Timing:** ~100ms

---

### 5.3 Get User Balance

**Endpoint:** `GET /api/expense/balance`  
**Auth:** Required

**Purpose:** Get authenticated user's balance across all groups

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_balance": -25.75, // Negative = you owe, Positive = owed to you
    "by_group": [
      {
        "group_id": "group-abc123",
        "group_name": "Apartment Roommates",
        "balance": -45.50,
        "currency": "USD"
      },
      {
        "group_id": "group-xyz789",
        "group_name": "Europe Trip",
        "balance": 19.75,
        "currency": "EUR"
      }
    ],
    "groups_count": 2
  }
}
```

**Timing:** ~30ms

---

### 5.4 Get Balance Breakdown

**Endpoint:** `GET /api/expense/balance/breakdown`  
**Auth:** Required

**Purpose:** Detailed breakdown of what you owe to each person

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_balance": -25.75,
    "you_owe": [
      {
        "to_user": {
          "uid": "user-123",
          "display_name": "John Doe"
        },
        "amount": 45.50,
        "group_name": "Apartment Roommates",
        "currency": "USD"
      }
    ],
    "owed_to_you": [
      {
        "from_user": {
          "uid": "user-789",
          "display_name": "Bob Johnson"
        },
        "amount": 19.75,
        "group_name": "Europe Trip",
        "currency": "EUR"
      }
    ],
    "total_you_owe": 45.50,
    "total_owed_to_you": 19.75
  }
}
```

**Timing:** ~50ms

---

### 5.5 Get Group Balances

**Endpoint:** `GET /api/expense/balance/group/{group_id}`  
**Auth:** Required (must be group member)

**Purpose:** Get all balances and settlement suggestions for a group

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "group_id": "group-abc123",
    "balances": [
      {
        "uid": "user-123",
        "display_name": "John Doe",
        "balance": 85.50, // Others owe John $85.50
        "currency": "USD"
      },
      {
        "uid": "user-456",
        "display_name": "Jane Smith",
        "balance": -45.50, // Jane owes $45.50
        "currency": "USD"
      },
      {
        "uid": "user-789",
        "display_name": "Bob Johnson",
        "balance": -40.00,
        "currency": "USD"
      }
    ],
    
    "simplified_debts": [
      {
        "from_uid": "user-456",
        "from_name": "Jane Smith",
        "to_uid": "user-123",
        "to_name": "John Doe",
        "amount": 45.50,
        "suggestion": "Jane pays John $45.50"
      },
      {
        "from_uid": "user-789",
        "from_name": "Bob Johnson",
        "to_uid": "user-123",
        "to_name": "John Doe",
        "amount": 40.00,
        "suggestion": "Bob pays John $40.00"
      }
    ],
    
    "summary": {
      "total_expenses": 1250.75,
      "settled_amount": 500.00,
      "outstanding_amount": 750.75,
      "member_count": 4
    }
  }
}
```

**Timing:**
- Cached: ~2ms ⚡ (formatted response cached)
- Cold: ~50ms

**Caching:**
- Cache key: `group_balance_formatted:GROUP_ID`
- TTL: 300 seconds (5 minutes)
- Invalidated on: Expense added, settlement created

**Algorithm:**
- Simplified debt algorithm minimizes number of transactions
- Example: If A owes B $10, B owes C $10, simplified to: A pays C $10 directly

---

## 6️⃣ Admin & Monitoring APIs

### 6.1 Health Check

**Endpoint:** `GET /api/expense/health`  
**Auth:** NOT required (public)

**Purpose:** Quick health check for load balancers

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T21:00:00.123Z",
  "version": "1.0.0"
}
```

**Timing:** <1ms

---

### 6.2 Detailed Health Check

**Endpoint:** `GET /api/expense/health/detailed`  
**Auth:** Required (admin)

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T21:00:00.123Z",
  "version": "1.0.0",
  "services": {
    "firebase": {
      "status": "healthy",
      "latency_ms": 45
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 2,
      "connected": true,
      "memory_used_mb": 8.5
    }
  },
  "uptime_seconds": 86400
}
```

**Timing:** ~50ms

---

### 6.3 Cache Statistics

**Endpoint:** `GET /api/expense/cache/stats`  
**Auth:** Required (admin)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_keys": 1250,
    "memory_used_mb": 8.5,
    "hit_rate": 0.92,
    "hits": 45000,
    "misses": 3900,
    "evictions": 120,
    "by_prefix": {
      "user_groups": {"count": 500, "memory_mb": 3.2},
      "display_name": {"count": 300, "memory_mb": 0.8},
      "group_full": {"count": 150, "memory_mb": 2.5},
      "balance": {"count": 200, "memory_mb": 1.5}
    }
  }
}
```

**Timing:** ~10ms

---

### 6.4 Detailed Cache Analytics

**Endpoint:** `GET /api/expense/cache/stats/detailed`  
**Auth:** Required (admin)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "overview": {
      "total_keys": 1250,
      "memory_used_mb": 8.5,
      "hit_rate": 0.92,
      "avg_ttl_seconds": 1800
    },
    "performance": {
      "avg_get_time_ms": 1.2,
      "avg_set_time_ms": 1.5,
      "p95_get_time_ms": 3.0,
      "p99_get_time_ms": 5.0
    },
    "by_type": {
      "user_groups": {
        "count": 500,
        "memory_mb": 3.2,
        "hit_rate": 0.95,
        "avg_ttl": 1800
      }
    }
  }
}
```

**Timing:** ~30ms

---

### 6.5 Warm Cache for User

**Endpoint:** `POST /api/expense/cache/warm`  
**Auth:** Required (admin)

**Purpose:** Pre-populate cache for a user (useful before high-traffic events)

**Request Body:**
```json
{
  "user_id": "user-123" // Optional, defaults to authenticated user
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Cache warmed successfully",
  "cached": {
    "user_profile": true,
    "user_groups": true,
    "display_names": 8,
    "group_details": 5
  },
  "time_ms": 250
}
```

**Timing:** ~250ms (populates multiple cache keys)

---

### 6.6 Performance Metrics

**Endpoint:** `GET /api/expense/metrics`  
**Auth:** Required (admin)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "requests": {
      "total": 50000,
      "success": 49500,
      "errors": 500,
      "success_rate": 0.99
    },
    "latency": {
      "avg_ms": 25,
      "p50_ms": 15,
      "p95_ms": 80,
      "p99_ms": 200
    },
    "firestore": {
      "reads": 5000,
      "writes": 1200,
      "cost_estimate_usd": 0.42
    },
    "cache": {
      "hit_rate": 0.92,
      "saves_count": 45000
    },
    "slow_queries": [
      {
        "endpoint": "GET /expenses/group/123",
        "avg_time_ms": 450,
        "count": 5
      }
    ]
  }
}
```

**Timing:** ~50ms

---

### 6.7 Rate Limit Status

**Endpoint:** `GET /api/expense/rate-limits`  
**Auth:** Required

**Purpose:** Check your current rate limit usage

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user_id": "user-123",
    "limits": {
      "standard": {
        "limit": 100,
        "remaining": 85,
        "reset_at": "2025-01-15T21:05:00Z"
      },
      "create_operations": {
        "limit": 30,
        "remaining": 28,
        "reset_at": "2025-01-15T21:05:00Z"
      }
    }
  }
}
```

**Timing:** ~5ms

---

### 6.8 Get Categories (Public)

**Endpoint:** `GET /api/expense/categories`  
**Auth:** NOT required

**Purpose:** Get list of available expense categories

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {"id": "FOOD", "label": "Food & Dining", "icon": "🍔"},
    {"id": "TRANSPORT", "label": "Transportation", "icon": "🚗"},
    {"id": "ENTERTAINMENT", "label": "Entertainment", "icon": "🎬"},
    {"id": "UTILITIES", "label": "Utilities", "icon": "💡"},
    {"id": "SHOPPING", "label": "Shopping", "icon": "🛍️"},
    {"id": "HOUSING", "label": "Housing", "icon": "🏠"},
    {"id": "OTHER", "label": "Other", "icon": "📦"}
  ]
}
```

**Timing:** <1ms (static data)

---

### 6.9 Get Split Types (Public)

**Endpoint:** `GET /api/expense/split-types`  
**Auth:** NOT required

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "EQUAL",
      "label": "Split Equally",
      "description": "Divide amount equally among all participants"
    },
    {
      "id": "PERCENTAGE",
      "label": "Split by Percentage",
      "description": "Each person pays a percentage of the total"
    },
    {
      "id": "CUSTOM",
      "label": "Custom Amounts",
      "description": "Specify exact amount for each person"
    },
    {
      "id": "SHARES",
      "label": "Split by Shares",
      "description": "Each person gets X shares of the total"
    }
  ]
}
```

**Timing:** <1ms (static data)

---

## 🚨 Error Codes Reference

### Standard Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Human-readable error message",
    "details": {
      "field": "amount",
      "reason": "Amount must be greater than 0"
    }
  },
  "timestamp": "2025-01-15T21:00:00.123Z"
}
```

### HTTP Status Codes

| Status | Meaning | Common Scenarios |
|--------|---------|------------------|
| 200 | OK | Successful GET/PUT/DELETE |
| 201 | Created | Successful POST (resource created) |
| 400 | Bad Request | Invalid input, missing fields, validation errors |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated but not authorized (permission denied) |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource (e.g., username taken) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error (bug) |
| 503 | Service Unavailable | Firestore or Redis down |

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request or missing required fields |
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `UNAUTHORIZED` | 401 | Not authenticated |
| `FORBIDDEN` | 403 | Not authorized (permission denied) |
| `NOT_FOUND` | 404 | Resource not found |
| `DUPLICATE` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `BALANCE_MISMATCH` | 400 | Splits don't add up to total |
| `INSUFFICIENT_PERMISSIONS` | 403 | Not owner/admin |
| `EXPIRED` | 400 | Invitation expired |
| `ALREADY_MEMBER` | 400 | User already in group |
| `UNSETTLED_BALANCE` | 400 | Cannot leave/delete with pending balance |
| `FIREBASE_ERROR` | 500 | Firestore operation failed |
| `REDIS_ERROR` | 500 | Redis operation failed |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Example Error Responses

**Validation Error:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "field": "splits",
      "reason": "Sum of splits (120.00) does not match amount (120.50)"
    }
  }
}
```

**Permission Denied:**
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Only group owner can delete the group"
  }
}
```

**Rate Limit:**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 100,
      "window": "1 minute",
      "reset_at": "2025-01-15T21:05:00Z"
    }
  }
}
```

---

## ⏱️ Rate Limiting

### Rate Limit Tiers

| Endpoint Type | Limit | Window | Header |
|---------------|-------|--------|--------|
| Standard (GET) | 100 req | 1 minute | `X-RateLimit-Standard` |
| Create (POST) | 30 req | 1 minute | `X-RateLimit-Create` |
| Delete | 20 req | 1 minute | `X-RateLimit-Delete` |
| Admin | 60 req | 1 minute | `X-RateLimit-Admin` |
| Public | Unlimited | - | N/A |

### Rate Limit Headers

**Every response includes:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1642272300
```

**When rate limited (429):**
```http
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642272300
```

### Rate Limit Best Practices

1. **Cache aggressively** on the client side
2. **Batch requests** when possible
3. **Handle 429 errors** with exponential backoff
4. **Check rate limit headers** before making more requests
5. **Use webhooks** instead of polling (future feature)

---

## ⚡ Performance Timing Summary

### Cached vs Cold Start Performance

| Endpoint | Cached | Cold | Cache Hit Rate |
|----------|--------|------|----------------|
| GET /groups (summary) | 5ms | 150ms | 95% |
| GET /groups (full) | 15ms | 400ms | 90% |
| GET /groups/{id}/full | 4ms | 180ms | 95% |
| GET /invitations | 3ms | 150ms | 85% |
| GET /balance/group/{id} | 2ms | 50ms | 89% |
| GET /expenses/group/{id} | 10ms | 300ms | 88% |
| POST /expenses | 50ms | 200ms | N/A |
| POST /settlements | N/A | 180ms | N/A |

### Performance Tips

1. **Use summary mode** for lists: `GET /groups?mode=summary` (5ms vs 15ms)
2. **Use /full endpoint** for group details (single request vs multiple)
3. **Implement client-side caching** with React Query (stale-while-revalidate)
4. **Use pagination** for large lists
5. **Batch display name fetching** (already done server-side)

---

**End of API Reference**
