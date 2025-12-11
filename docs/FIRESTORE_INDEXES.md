# Firestore Indexes Documentation

This document explains all the composite indexes defined in `firestore.indexes.json`.

## Overview

Firestore requires composite indexes for any query that:
1. Filters on one field AND orders by a different field
2. Filters on multiple fields
3. Uses array-contains with any orderBy

## Collections & Indexes

### 1. expense_expenses (5 indexes)

| Index | Fields | Purpose |
|-------|--------|---------|
| 1 | `group_id` + `is_deleted` + `expense_date DESC` | **Frontend listener** - Real-time expense updates with soft delete filter |
| 2 | `group_id` + `expense_date DESC` | Basic pagination for group expenses |
| 3 | `group_id` + `category` + `expense_date DESC` | Filter expenses by category |
| 4 | `group_id` + `linked_expense_id` | Find linked/recurring expenses |
| 5 | `participants (array_contains)` + `expense_date DESC` | Get expenses for a specific user |

### 2. expense_settlements (5 indexes)

| Index | Fields | Purpose |
|-------|--------|---------|
| 1 | `group_id` + `created_at DESC` | **Frontend listener** - Real-time settlement updates |
| 2 | `group_id` + `status` + `created_at DESC` | Filter settlements by status (pending/completed) |
| 3 | `group_id` + `is_deleted` + `created_at DESC` | Settlement list with soft delete filter |
| 4 | `payer_id` + `created_at DESC` | Get settlements where user is payer |
| 5 | `receiver_id` + `created_at DESC` | Get settlements where user is receiver |

### 3. expense_groups (2 indexes)

| Index | Fields | Purpose |
|-------|--------|---------|
| 1 | `members (array_contains)` + `created_at DESC` | Get all groups for a user |
| 2 | `members (array_contains)` + `is_active` + `created_at DESC` | Get active/inactive groups for a user |

### 4. expense_invitations (5 indexes)

| Index | Fields | Purpose |
|-------|--------|---------|
| 1 | `group_id` + `created_at DESC` | Get all invitations for a group |
| 2 | `group_id` + `status` | Get invitations by status for a group |
| 3 | `email` + `status` + `created_at DESC` | Get invitations for a user by email |
| 4 | `status` + `expires_at` | Find expired invitations for cleanup |
| 5 | `group_id` + `invitee_email` + `status` + `expires_at` | Check existing invitation before creating |

### 5. expense_group_members (2 indexes)

| Index | Fields | Purpose |
|-------|--------|---------|
| 1 | `group_id` + `is_active` | Get active/inactive members of a group |
| 2 | `user_id` + `is_active` | Get all group memberships for a user |

## Deployment

Deploy indexes to Firebase:

```bash
firebase deploy --only firestore:indexes
```

## Important Notes

1. **Index building takes time** - New indexes can take several minutes to build for collections with existing data.

2. **Index limits** - Firebase allows up to 200 composite indexes per database.

3. **Single-field indexes** - These are created automatically by Firestore. Only composite indexes need to be defined.

4. **Order matters** - The order of fields in a composite index must match your query's filter/orderBy sequence.

## Query Examples

### Frontend Listener Query (expense_expenses)
```javascript
collection("expense_expenses")
  .where("group_id", "==", groupId)
  .where("is_deleted", "==", false)
  .orderBy("expense_date", "desc")
  .limit(50)
```

### Frontend Listener Query (expense_settlements)
```javascript
collection("expense_settlements")
  .where("group_id", "==", groupId)
  .orderBy("created_at", "desc")
  .limit(50)
```

### Backend Repository Query (invitations)
```python
db.collection("expense_invitations")
  .where("group_id", "==", group_id)
  .where("status", "==", "pending")
  .stream()
```

## Troubleshooting

If you see an error like:
```
The query requires an index. You can create it here: <URL>
```

1. Click the URL to create the index in Firebase Console
2. OR add the index to `firestore.indexes.json` and deploy

## Total Indexes: 19

This covers all query patterns used in:
- `expense_engine/repositories/*.py` (backend)
- `web/frontend/src/services/expense/expenseFirestoreListener.js` (frontend)
