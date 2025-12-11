# Expense Management System - Complete Architecture and Flow Documentation

## Overview

This is a **Splitwise-like expense management system** built with:
- **Frontend**: React.js with React Query for state management
- **Backend**: Python/Flask REST API
- **Database**: Firebase Firestore (NoSQL)
- **Real-time**: Firestore listeners for instant updates
- **Cache**: Redis for performance optimization
- **Email**: SMTP-based email notifications

---

## 1. Firebase Collections (Database Schema)

### 1.1 Core Collections

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `expense_groups` | Group information | `name`, `created_by`, `members[]`, `member_details{}`, `group_code`, `currency`, `is_active` |
| `expense_group_members` | Membership records | `group_id`, `user_id`, `role`, `is_active`, `joined_at`, `display_name` |
| `expense_expenses` | Transaction records | `group_id`, `description`, `amount`, `paid_by`, `splits[]`, `category`, `is_deleted` |
| `expense_settlements` | Payment settlements | `group_id`, `from_user_id`, `to_user_id`, `amount`, `method`, `is_deleted` |
| `expense_invitations` | Group invitations | `group_id`, `email`, `invited_by`, `status`, `expires_at` |
| `expense_group_balances` | Cached balances | `group_id`, `balances{}` (user_id → amount) |
| `users` | User profiles | `uid`, `email`, `display_name`, `photo_url` |

### 1.2 Document ID Conventions

```
expense_groups/{groupId}                  → Auto-generated Firestore ID
expense_group_members/{groupId}_{userId}  → Composite key for fast lookups
expense_expenses/{expenseId}              → Auto-generated
expense_settlements/{settlementId}        → Auto-generated
expense_invitations/{invitationId}        → Auto-generated
expense_group_balances/{groupId}          → Same as group ID
```

---

## 2. Firestore Indexes

The system uses composite indexes for optimized queries (defined in `firestore.indexes.json`):

```json
// Expenses by group + date
{ "group_id": ASC, "expense_date": DESC }

// Expenses by group + category + date
{ "group_id": ASC, "category": ASC, "expense_date": DESC }

// Expenses by group + soft delete + date
{ "group_id": ASC, "is_deleted": ASC, "expense_date": DESC }

// Expenses by group + linked expense
{ "group_id": ASC, "linked_expense_id": ASC }

// Settlements by group + status + date
{ "group_id": ASC, "status": ASC, "created_at": DESC }

// Settlements by group + soft delete + date
{ "group_id": ASC, "is_deleted": ASC, "created_at": DESC }

// Invitations by group + status
{ "group_id": ASC, "status": ASC }

// Group members by group + active status
{ "group_id": ASC, "is_active": ASC }

// Group members by user + active status (for user's groups lookup)
{ "user_id": ASC, "is_active": ASC }

// Groups by members array + active + created date
{ "members": ARRAY_CONTAINS, "is_active": ASC, "created_at": DESC }
```

---

## 3. Security Rules (Firestore Rules)

### 3.1 Role Hierarchy

```
OWNER → Full control (create, delete group, manage all)
ADMIN → Manage members, expenses, settlements
MEMBER → Create/edit own expenses, view group data
```

### 3.2 Key Rules (from `firestore.rules`)

```javascript
// Helper: Check if user is group member
function isGroupMember(groupId) {
  return exists(/databases/$(database)/documents/expense_group_members/$(groupId + '_' + userId())) &&
         getMembership(groupId).data.is_active == true;
}

// Helper: Check if user is group admin
function isGroupAdmin(groupId) {
  return hasRole(groupId, 'owner') || hasRole(groupId, 'admin');
}

// Groups: Only members can read, owner can delete
match /expense_groups/{groupId} {
  allow read: if isGroupMember(groupId);
  allow create: if isAuthenticated() &&
                   request.resource.data.created_by == userId() &&
                   request.resource.data.members.hasAll([userId()]);
  allow update: if isGroupAdmin(groupId) &&
                   request.resource.data.created_by == resource.data.created_by;
  allow delete: if isGroupOwner(groupId);
}

// Expenses: Members can create, only creator/admin can edit/delete
match /expense_expenses/{expenseId} {
  allow read: if isGroupMember(resource.data.group_id);
  allow create: if isAuthenticated() &&
                   isGroupMember(request.resource.data.group_id) &&
                   request.resource.data.created_by == userId() &&
                   isPositiveNumber('amount');
  allow update: if isAuthenticated() &&
                   isGroupMember(resource.data.group_id) &&
                   (resource.data.created_by == userId() || 
                    isGroupAdmin(resource.data.group_id));
  allow delete: if isAuthenticated() &&
                   isGroupMember(resource.data.group_id) &&
                   (resource.data.created_by == userId() || 
                    isGroupAdmin(resource.data.group_id));
}

// Settlements: Members can create, payer/receiver/admin can update
match /expense_settlements/{settlementId} {
  allow read: if isGroupMember(resource.data.group_id);
  allow create: if isAuthenticated() &&
                   isGroupMember(request.resource.data.group_id) &&
                   isPositiveNumber('amount');
  allow update: if isAuthenticated() &&
                   isGroupMember(resource.data.group_id) &&
                   (resource.data.from_user_id == userId() ||
                    resource.data.to_user_id == userId() ||
                    isGroupAdmin(resource.data.group_id));
  allow delete: if isGroupAdmin(resource.data.group_id);
}

// Invitations: Invitee or group members can read
match /expense_invitations/{invitationId} {
  allow read: if isAuthenticated() &&
                (resource.data.email == request.auth.token.email ||
                 isGroupMember(resource.data.group_id));
  allow create: if isAuthenticated() &&
                   isGroupAdmin(request.resource.data.group_id);
  allow update: if isAuthenticated();  // Invitee can accept/decline
  allow delete: if isGroupAdmin(resource.data.group_id);
}

// Group Balances: Read-only for members (backend writes only)
match /expense_group_balances/{balanceId} {
  allow read: if isGroupMember(balanceId);
  allow write: if false;  // Only backend can write
}
```

---

## 4. Complete Workflows

### 4.1 CREATE GROUP Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Frontend   │────▶│  Backend API │────▶│      Firestore       │
│ (React.js)   │     │ (Flask/Py)   │     │                      │
└──────────────┘     └──────────────┘     └──────────────────────┘

1. User clicks "Create Group" → POST /api/expense/groups
   {
     "name": "Trip to Paris",
     "description": "Summer vacation",
     "currency": "EUR"
   }

2. Backend GroupService.create_group():
   a. Generate unique group_code (8 chars alphanumeric)
   b. Create Group model with creator as first member (role: admin)
   c. Write to expense_groups collection
   d. Create expense_group_members/{groupId}_{creatorId} document
   e. Initialize expense_group_balances/{groupId} with empty balances

3. Firestore Collections Updated:
   expense_groups/{groupId} ← Group document
   expense_group_members/{groupId}_{userId} ← Creator as admin
   expense_group_balances/{groupId} ← Empty balances {}

4. Real-time listener triggers → Frontend auto-updates
```

**Code Path:**
```
Frontend: expenseApi.createGroup() → POST /api/expense/groups
Backend:  group_routes.py:create_group() → GroupService.create_group()
Repository: GroupRepository.create() → Firestore write
```

---

### 4.2 SEND INVITATION Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  Backend API │────▶│  Firestore   │────▶│ Email Worker │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

1. Admin clicks "Invite Member" → POST /api/expense/invitations
   {
     "group_id": "abc123",
     "invited_email": "friend@email.com",
     "role": "member"
   }

2. Backend InvitationService.create_invitation():
   a. Verify inviter is admin/owner of group
   b. Check if invitation already exists (prevent duplicates)
   c. Check max members limit (default: 50)
   d. Calculate expires_at (7 days from now)
   e. Enrich with group_name and inviter_name
   f. Write to expense_invitations collection
   g. Queue email notification via EmailWorker

3. Email Service (Async):
   - Check if invitation emails enabled (email_config)
   - Send HTML email with:
     - Inviter name
     - Group name
     - Accept invitation button/link
   - Link format: /accept-invitation?id={invitationId}&type=expense

4. Invitation Document Created:
   expense_invitations/{invitationId} = {
     group_id: "abc123",
     group_name: "Trip to Paris",
     email: "friend@email.com",
     invited_by: "user123",
     invited_by_name: "John Doe",
     status: "pending",
     expires_at: <7 days from now>
   }
```

**Code Path:**
```
Frontend: expenseApi.sendInvitation() → POST /api/expense/invitations
Backend:  invitation_routes.py:create_invitation() → InvitationService.create_invitation()
Email:    EmailService.send_group_invitation() via EmailWorker.queue_email()
```

---

### 4.3 ACCEPT INVITATION Flow

```
┌──────────────┐     ┌──────────────┐     ┌────────────────────────────┐
│  Invitee     │────▶│  Backend API │────▶│        Firestore           │
│ (clicks link)│     │              │     │                            │
└──────────────┘     └──────────────┘     └────────────────────────────┘

1. Invitee clicks email link → GET /accept-invitation?id={invitationId}

2. Frontend fetches invitation details (NO AUTH REQUIRED):
   GET /api/expense/invitations/{invitationId}/details
   Response: { group_name, invited_by_name, status }

3. If user signs in/up → POST /api/expense/invitations/{invitationId}/accept

4. Backend InvitationService.accept_invitation():
   a. Verify invitation status == "pending"
   b. Verify not expired
   c. Update invitation status to "accepted"
   d. Add user to group via GroupRepository.add_member():
      - Update expense_groups/{groupId}.members array
      - Create expense_group_members/{groupId}_{userId}
      - Initialize user balance in expense_group_balances

5. Collections Updated:
   expense_invitations/{invitationId}.status = "accepted"
   expense_groups/{groupId}.members += [userId]
   expense_group_members/{groupId}_{userId} = { role: "member", is_active: true }

6. Frontend redirects to /expenses?group={groupId}
```

**Invitation Status Flow:**
```
PENDING → ACCEPTED (user accepts)
PENDING → DECLINED (user declines)
PENDING → EXPIRED (7 days passed)
PENDING → CANCELLED (admin revokes)
```

---

### 4.4 ADD EXPENSE Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Frontend   │────▶│  Backend API │────▶│     Firestore        │
│              │     │ (Transaction)│     │   + Balance Update   │
└──────────────┘     └──────────────┘     └──────────────────────┘

1. User fills expense form → POST /api/expense/groups/{groupId}/expenses
   {
     "description": "Dinner at restaurant",
     "amount": 150.00,
     "paid_by": "user123",
     "split_type": "equal",
     "splits": [
       {"user_id": "user123", "amount": 50.00},
       {"user_id": "user456", "amount": 50.00},
       {"user_id": "user789", "amount": 50.00}
     ],
     "category": "food"
   }

2. Backend ExpenseService.create_expense() [TRANSACTIONAL]:
   a. Validate all split users are group members
   b. Validate splits sum equals total amount
   c. Create expense document in expense_expenses
   d. Calculate balance deltas via BalanceService.calculate_expense_deltas():
      - Payer gets CREDIT: +$150 (they paid)
      - Each participant gets DEBIT: -$50 (they owe)
      - Net for payer: +150 - 50 = +100 (they are owed $100)
   e. Apply deltas to expense_group_balances/{groupId}

3. Balance Calculation Logic:
   Before: { user123: 0, user456: 0, user789: 0 }
   
   Payer (user123) paid $150, owes $50:
     user123: +150 - 50 = +100 (is owed $100)
   
   Participants owe their share:
     user456: -50 (owes $50)
     user789: -50 (owes $50)
   
   After: { user123: +100, user456: -50, user789: -50 }
   
   Interpretation:
   - user123 is OWED $100 (positive balance)
   - user456 OWES $50 (negative balance)
   - user789 OWES $50 (negative balance)
   - Sum = 0 (always balanced!)
```

**Code Path:**
```
Frontend: expenseApi.createExpense() → POST /api/expense/groups/{gid}/expenses
Backend:  expense_routes.py:create_expense() → ExpenseService.create_expense()
Balance:  BalanceService.add_expense_to_balances() → Firestore transaction
```

---

### 4.5 EDIT EXPENSE Flow

```
PATCH /api/expense/groups/{groupId}/expenses/{expenseId}

1. ExpenseService.update_expense() [TRANSACTIONAL]:
   a. Verify user is expense creator OR group admin
   b. Get old expense data
   c. Create new expense model with updates
   d. Calculate balance changes via BalanceService.edit_expense_in_balances():
      - REVERSE old expense deltas
      - APPLY new expense deltas
   e. Update expense document

2. Balance Update Example:
   Old expense: $150 split 3 ways
   New expense: $180 split 3 ways (amount changed)
   
   Reverse old: user123 -100, user456 +50, user789 +50
   Apply new:   user123 +120, user456 -60, user789 -60
   Net change:  user123 +20, user456 -10, user789 -10
```

---

### 4.6 DELETE EXPENSE Flow

```
DELETE /api/expense/groups/{groupId}/expenses/{expenseId}

1. ExpenseService.delete_expense() [TRANSACTIONAL]:
   a. Verify user is expense creator OR group admin
   b. Get expense data for balance reversal
   c. Soft-delete expense (is_deleted = true, deleted_at = now)
   d. REVERSE balance deltas:
      - Original: payer +100, participant1 -50, participant2 -50
      - Reversal: payer -100, participant1 +50, participant2 +50

2. Collections Updated:
   expense_expenses/{expenseId}.is_deleted = true
   expense_group_balances/{groupId}.balances updated (reversed)
```

**Key Point:** Expenses are **soft-deleted** - they're marked `is_deleted: true` but not removed from Firestore. This preserves audit trail and allows restoration.

---

### 4.7 CREATE SETTLEMENT Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Frontend   │────▶│  Backend API │────▶│     Firestore        │
│              │     │ (Transaction)│     │                      │
└──────────────┘     └──────────────┘     └──────────────────────┘

1. User records payment → POST /api/expense/groups/{groupId}/settlements
   {
     "from_user_id": "user456",  // Person paying
     "to_user_id": "user123",    // Person receiving
     "amount": 50.00,
     "method": "venmo",
     "notes": "Dinner payment"
   }

2. Backend SettlementService.create_settlement() [TRANSACTIONAL]:
   a. Validate both users are group members
   b. Validate users are different (can't settle with yourself)
   c. Create settlement document
   d. Update balances via BalanceService.add_settlement_to_balances():
      - from_user balance INCREASES (they owe less)
      - to_user balance DECREASES (they are owed less)

3. Balance Update:
   Before: { user123: +100, user456: -50 }
   
   user456 pays user123 $50:
     user456: -50 + 50 = 0 (debt cleared)
     user123: +100 - 50 = +50 (still owed $50 by user789)
   
   After: { user123: +50, user456: 0, user789: -50 }
```

**Settlement Methods (Enum):**
- `cash`, `bank_transfer`, `upi`, `zelle`, `venmo`, `paypal`, `other`

---

## 5. Ownership and Permissions

### 5.1 Who is the Group Owner?

```python
# The owner is the user in created_by field
group = {
    "created_by": "user123",  # ← THIS IS THE OWNER
    "members": ["user123", "user456", "user789"]
}

# In expense_group_members, the owner has role="admin" (or "owner")
expense_group_members/{groupId}_{user123} = {
    "role": "admin",  # First member is always admin
    "is_active": true
}
```

### 5.2 Permission Matrix

| Action | Owner | Admin | Member |
|--------|-------|-------|--------|
| View group | ✅ | ✅ | ✅ |
| Edit group settings | ✅ | ✅ | ❌ |
| Delete group | ✅ | ❌ | ❌ |
| Invite members | ✅ | ✅ | ❌ |
| Remove members | ✅ | ✅ | ❌ |
| Create expense | ✅ | ✅ | ✅ |
| Edit any expense | ✅ | ✅ | ❌ |
| Edit own expense | ✅ | ✅ | ✅ |
| Delete any expense | ✅ | ✅ | ❌ |
| Delete own expense | ✅ | ✅ | ✅ |
| Create settlement | ✅ | ✅ | ✅ |

### 5.3 Role Definitions

```python
class GroupRole(str, Enum):
    OWNER = "owner"   # Created the group, full control
    ADMIN = "admin"   # Can manage members and expenses
    MEMBER = "member" # Can only create/edit own expenses
```

---

## 6. Email Service Architecture

### 6.1 Email Types

```python
# Email types with enable/disable per type
email_types = {
    'invitation': True,      # Group invitation emails
    'expense_added': False,  # New expense notification
    'settlement': False,     # Settlement recorded
    'reminder': False        # Balance reminder
}
```

### 6.2 Email Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Service    │────▶│ EmailWorker  │────▶│ EmailService │────▶│ SMTP Server  │
│ (async call) │     │   (Queue)    │     │              │     │ (Gmail etc)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

1. InvitationService calls:
   email_worker.queue_email(
     email_type='invitation',
     recipients=['friend@email.com'],
     data={
       'inviter_name': 'John',
       'group_name': 'Trip to Paris',
       'invitation_link': 'http://app/accept?id=xxx'
     }
   )

2. EmailWorker processes queue (background thread)

3. EmailService.send_group_invitation() sends HTML email

4. Environment variables required:
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your@gmail.com
   SMTP_PASSWORD=app_password
   FROM_EMAIL=noreply@yourapp.com
```

### 6.3 Invitation Email Template

The email includes:
- App branding header
- "You've been invited to join a group!" message
- Inviter name and group name
- Benefits list (share expenses, track balances, settle easily)
- "Accept Invitation" button
- 7-day expiry notice
- Footer with unsubscribe link

---

## 7. Real-Time Updates (Firestore Listeners)

### 7.1 Collections Monitored

```javascript
// ExpenseFirestoreListener.js monitors:
- expense_groups/{groupId}           → Group changes
- expense_group_members (query)      → Membership changes
- expense_expenses (query)           → Expense changes
- expense_group_balances/{groupId}   → Balance changes
- expense_settlements (query)        → Settlement changes
- expense_invitations (query)        → Invitation changes
```

### 7.2 Listener Setup

```javascript
// When user opens a group:
subscribeToGroup(groupId, callbacks) {
  // 1. Listen to group document
  onSnapshot(doc(db, 'expense_groups', groupId), (doc) => {
    callbacks.onGroupUpdate(doc.data());
  });
  
  // 2. Listen to expenses for this group
  const expensesQuery = query(
    collection(db, 'expense_expenses'),
    where('group_id', '==', groupId),
    where('is_deleted', '==', false),
    orderBy('expense_date', 'desc'),
    limit(100)
  );
  onSnapshot(expensesQuery, callbacks.onExpensesUpdate);
  
  // 3. Listen to balances
  onSnapshot(
    doc(db, 'expense_group_balances', groupId),
    callbacks.onBalancesUpdate
  );
  
  // 4. Listen to settlements
  const settlementsQuery = query(
    collection(db, 'expense_settlements'),
    where('group_id', '==', groupId),
    where('is_deleted', '==', false),
    orderBy('created_at', 'desc')
  );
  onSnapshot(settlementsQuery, callbacks.onSettlementsUpdate);
}
```

### 7.3 Benefits of Real-Time Listeners

- **Zero API calls** - Direct Firestore connection
- **Instant updates** - ~50-100ms latency
- **Free reads** - Snapshot listeners don't count towards quota after initial read
- **Auto reconnection** - Built into Firebase SDK
- **Offline support** - Works with Firebase cache

---

## 8. API Endpoints Reference

### 8.1 User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/expense/user/profile` | Get current user profile |
| PUT | `/api/expense/user/profile` | Update user profile |
| GET | `/api/expense/user/groups` | Get user's groups |
| GET | `/api/expense/user/search` | Search users |

### 8.2 Group Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/expense/groups` | Create group |
| GET | `/api/expense/groups/{id}` | Get group |
| GET | `/api/expense/groups/{id}/full` | Get group + members + balances |
| PATCH | `/api/expense/groups/{id}` | Update group |
| DELETE | `/api/expense/groups/{id}` | Delete group |
| GET | `/api/expense/groups/{id}/members` | List members |
| POST | `/api/expense/groups/{id}/members` | Add member |
| DELETE | `/api/expense/groups/{id}/members/{uid}` | Remove member |

### 8.3 Expense Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/expense/groups/{gid}/expenses` | Create expense |
| GET | `/api/expense/groups/{gid}/expenses` | List expenses (paginated) |
| GET | `/api/expense/groups/{gid}/expenses/{eid}` | Get expense |
| PATCH | `/api/expense/groups/{gid}/expenses/{eid}` | Update expense |
| DELETE | `/api/expense/groups/{gid}/expenses/{eid}` | Delete expense (soft) |

### 8.4 Settlement Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/expense/groups/{gid}/settlements` | Create settlement |
| GET | `/api/expense/groups/{gid}/settlements` | List settlements |
| GET | `/api/expense/groups/{gid}/settlements/{sid}` | Get settlement |
| DELETE | `/api/expense/groups/{gid}/settlements/{sid}` | Delete settlement |

### 8.5 Invitation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/expense/invitations` | Send invitation |
| GET | `/api/expense/invitations/{id}/details` | Get details (public, no auth) |
| POST | `/api/expense/invitations/{id}/accept` | Accept invitation |
| POST | `/api/expense/invitations/{id}/decline` | Decline invitation |
| DELETE | `/api/expense/invitations/{id}` | Revoke invitation |
| GET | `/api/expense/invitations/user` | User's pending invitations |
| GET | `/api/expense/invitations/group/{gid}` | Group's invitations |

---

## 9. Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React.js)                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Expense    │  │ Group      │  │ Settlement │  │ Pending    │            │
│  │ Manager    │  │ Balances   │  │ History    │  │ Invitations│            │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
│        │               │               │               │                    │
│        └───────────────┴───────────────┴───────────────┘                    │
│                              │                                              │
│                    ┌─────────▼─────────┐                                    │
│                    │   expenseApi.js   │ ←── API calls                      │
│                    └─────────┬─────────┘                                    │
│                              │                                              │
│     ┌────────────────────────┼────────────────────────┐                     │
│     │                        │                        │                     │
│     ▼                        ▼                        ▼                     │
│  HTTP Requests        Firestore Listeners       React Query                 │
│  (Create/Update)      (Real-time reads)         (Cache)                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Flask Backend     │
                    │   /api/expense/*    │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ Group Service│   │Expense Service│  │Invite Service│
    └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
           │                  │                   │
           │                  │                   │
           └──────────────────┼───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Balance Service   │ ←── Incremental updates
                    └─────────┬─────────┘     (never full recalc)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Group Repo   │ │ Expense Repo │ │ Balance Repo │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                 │
           └────────────────┼─────────────────┘
                            │
                   ┌────────▼────────┐
                   │    FIRESTORE    │
                   │                 │
                   │ expense_groups  │
                   │ expense_expenses│
                   │ expense_members │
                   │ expense_balances│
                   │ expense_settl.  │
                   │ expense_invites │
                   └─────────────────┘
```

---

## 10. Key Architectural Decisions

### 10.1 Design Principles

1. **Incremental Balance Updates**
   - Never recalculate all balances from scratch
   - Always apply deltas (+/-) atomically
   - Sum of all balances always equals zero

2. **Soft Deletes**
   - Expenses/settlements use `is_deleted: true` flag
   - Preserves audit trail
   - Allows future restoration feature

3. **Denormalized Data**
   - User names stored in expense/settlement documents
   - Group name stored in invitation documents
   - Reduces reads, accepts slight staleness

4. **Composite Keys**
   - `{groupId}_{userId}` for membership documents
   - Enables O(1) membership lookups
   - Single document read vs query

5. **Transactional Updates**
   - Expense + balance updates are atomic
   - Uses Firestore transactions
   - Prevents inconsistent states

6. **Real-time Listeners**
   - Direct Firestore connection for reads
   - Bypasses API for faster updates
   - Backend only for writes

7. **Async Email**
   - Non-blocking email sends
   - Failures don't break invitation creation
   - Background worker with retry logic

### 10.2 Constants and Limits

```python
# From expense_engine/config.py
MAX_GROUP_MEMBERS = 50
MAX_EXPENSE_AMOUNT = 1000000.00
MIN_EXPENSE_AMOUNT = 0.01
MAX_GROUP_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
BALANCE_PRECISION = 2  # Decimal places
SETTLEMENT_TOLERANCE = 0.01  # For rounding errors
INVITATION_EXPIRY_DAYS = 7
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
```

### 10.3 Split Types Supported

```python
class SplitType(str, Enum):
    EQUAL = "equal"        # Split equally among participants
    PERCENTAGE = "percentage"  # Split by percentage
    SHARES = "shares"      # Split by share count
    EXACT = "exact"        # Exact amounts per person
```

### 10.4 Expense Categories

```python
class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    OTHER = "other"
```

---

## 11. File Structure Reference

### 11.1 Backend Structure

```
web/backend/expense_engine/
├── __init__.py
├── config.py              # Configuration and constants
├── constants.py           # Enums (SplitType, Currency, etc.)
├── exceptions.py          # Custom exceptions
├── email_service.py       # Email sending logic
│
├── models/
│   ├── group.py          # Group, GroupMember, GroupSettings
│   ├── expense.py        # Expense, ExpenseSplit
│   ├── settlement.py     # Settlement, PaymentProof
│   ├── invitation.py     # Invitation
│   ├── balance.py        # Balance, GroupBalance
│   └── user.py           # UserProfile, UserPreferences
│
├── repositories/
│   ├── base.py           # BaseRepository (CRUD)
│   ├── group_repository.py
│   ├── expense_repository.py
│   ├── settlement_repository.py
│   ├── invitation_repository.py
│   ├── balance_repository.py
│   └── user_repository.py
│
├── services/
│   ├── group_service.py      # Group business logic
│   ├── expense_service.py    # Expense CRUD + balance
│   ├── settlement_service.py # Settlement CRUD + balance
│   ├── invitation_service.py # Invitation lifecycle
│   └── balance_service.py    # Incremental balance engine
│
├── routes/
│   ├── group_routes.py       # /api/expense/groups/*
│   ├── expense_routes.py     # /api/expense/groups/*/expenses/*
│   ├── settlement_routes.py  # /api/expense/groups/*/settlements/*
│   ├── invitation_routes.py  # /api/expense/invitations/*
│   └── user_routes.py        # /api/expense/user/*
│
├── middleware/
│   ├── auth.py           # @require_auth decorator
│   ├── rbac.py           # Role-based access control
│   └── rate_limiter.py   # Rate limiting
│
└── workers/
    └── email_worker.py   # Background email queue
```

### 11.2 Frontend Structure

```
web/frontend/src/
├── components/expenses/
│   ├── ExpenseManager.jsx      # Main container
│   ├── ExpenseSummary.jsx      # Summary cards
│   ├── TransactionList.jsx     # Expense list
│   ├── TransactionModal.jsx    # Add/edit expense
│   ├── GroupManager.jsx        # Group CRUD
│   ├── GroupBalances.jsx       # Balance display
│   ├── GroupSummaryCards.jsx   # Group stats
│   ├── SettlementModal.jsx     # Record payment
│   ├── SettlementHistory.jsx   # Settlement list
│   ├── PendingInvitations.jsx  # User's invitations
│   └── ModeToggle.jsx          # Personal/Group toggle
│
├── services/
│   ├── expenseApi.js               # REST API client
│   └── expenseFirestoreListener.js # Real-time listeners
│
└── hooks/
    ├── useExpense.js          # Auth & personal expenses
    └── useExpenseQuery.js     # React Query hooks
```

---

## 12. Quick Reference: Common Operations

### Create Group
```javascript
// Frontend
await expenseApi.createGroup({ name: 'Trip', currency: 'USD' });

// Backend creates:
// - expense_groups/{id}
// - expense_group_members/{id}_{userId}
// - expense_group_balances/{id}
```

### Invite Member
```javascript
// Frontend
await expenseApi.sendInvitation({ group_id: 'xxx', invited_email: 'a@b.com' });

// Backend creates:
// - expense_invitations/{id} with status: 'pending'
// - Sends email with accept link
```

### Accept Invitation
```javascript
// Frontend
await expenseApi.acceptInvitation(invitationId);

// Backend updates:
// - expense_invitations/{id}.status = 'accepted'
// - expense_groups/{gid}.members += [userId]
// - Creates expense_group_members/{gid}_{userId}
```

### Add Expense
```javascript
// Frontend
await expenseApi.createExpense(groupId, {
  description: 'Dinner',
  amount: 100,
  paid_by: userId,
  splits: [...]
});

// Backend creates:
// - expense_expenses/{id}
// - Updates expense_group_balances/{gid}
```

### Record Settlement
```javascript
// Frontend
await expenseApi.createSettlement(groupId, {
  from_user_id: 'debtor',
  to_user_id: 'creditor',
  amount: 50
});

// Backend creates:
// - expense_settlements/{id}
// - Updates expense_group_balances/{gid}
```

---

*Last Updated: November 2025*
