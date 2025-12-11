# Phase 17.9: Bug Fixes and Cache Optimization

**Date:** Session 3-4 - After Phase 17.8
**Status:** Complete

---

## Bug Fixes

### Bug 1: User B Doesn't See Invitation Instantly
**Problem:** When User A sends invitation, User B doesn't see it in their pending list.

**Root Cause:** Email case sensitivity mismatch. Firestore query used `currentUser.email` but invitations stored with lowercase email.

**Fix Location:** `ExpenseManager.jsx` line ~476

```javascript
// Before
email: currentUser.email

// After  
email: currentUser.email.toLowerCase().trim()
```

---

### Bug 2: Group Deletion Requires Two Clicks
**Problem:** Clicking delete on a group required clicking twice.

**Root Cause:** Race condition - Firestore listener cleanup wasn't completing before navigation.

**Fix Location:** `ExpenseManager.jsx` - `handleDeleteGroup` function

**Changes:**
1. Added explicit listener unsubscription before delete
2. Added 100ms delay for cleanup to complete
3. Added retry logic (3 attempts, 200ms delay between)
4. Added error feedback if all retries fail

```javascript
// Added cleanup delay
await new Promise(resolve => setTimeout(resolve, 100));

// Added retry logic
for (let attempt = 0; attempt < 3; attempt++) {
  const result = await mutateAsync({ groupId: selectedGroupId });
  if (result.success) break;
  await new Promise(resolve => setTimeout(resolve, 200));
}
```

---

### Bug 3: Expense Deletion Causes Miscalculations and History Disappearance
**Problem:** After deleting an expense, balances showed wrong values and expenses disappeared from history.

**Root Cause:** Firestore listener was overwriting optimistic updates before backend confirmation.

**Fix Location:** `ExpenseManager.jsx` - expense delete handler and Firestore listener

**Changes:**
1. Added `startMutationCooldown()` before delete mutation (5 second protection)
2. Added smart expense merging in Firestore listener to preserve optimistic deletes

```javascript
// Before delete mutation
startMutationCooldown();

// Smart merge logic
const mergedExpenses = currentExpenses.map(existing => {
  const firestoreVersion = expensesMap.get(existing.id);
  if (!firestoreVersion && existing.is_deleted) {
    return existing; // Keep optimistic delete
  }
  return firestoreVersion || existing;
});
```

---

### Bug 4: Settlement Receiver Doesn't See Updated Balances (Session 4)
**Problem:** After settlement, the owner (receiver who was owed money) didn't see the updated balance values, but the payer did.

**Root Cause:** In Phase 17.9, we removed ALL mega-bootstrap invalidation for settlements. But the receiver doesn't have optimistic updates (only the payer does).

**Fix Location:** `settlement_service.py` - `_invalidate_settlement_cache()`

**Changes:**
1. Added `receiver_id` parameter to function
2. Invalidate only the RECEIVER's mega-bootstrap cache

```python
def _invalidate_settlement_cache(self, group_id: str, receiver_id: str = None) -> None:
    # ... existing cache invalidation ...
    
    # Phase 17.9: Only invalidate RECEIVER's mega-bootstrap
    # - Payer (from_user): Has optimistic update from frontend mutation
    # - Receiver (to_user): Needs cache invalidation to see updated balance
    if receiver_id:
        cache.delete(f"expense:mega_bootstrap:{receiver_id}")
        cache.delete(f"expense:mega_bootstrap:{receiver_id}:{group_id}")
```

---

## Phase 17.9 Optimization: Selective Cache Invalidation

### Problem Identified
Session 3 logs showed `/user/groups` called 22 times per session - excessive.

**Root Cause:** Every expense/settlement/invitation mutation invalidated mega-bootstrap cache for ALL group members, causing cascade of re-fetches.

### Solution: Selective Invalidation
Only invalidate cache for the ACTING user. Other users receive updates via Firestore real-time listeners.

### Files Modified

#### 1. `expense_service.py` - `_invalidate_expense_cache()`
```python
# Phase 17.9: Only invalidate PAYER's mega-bootstrap (not all members)
# Other members receive updates via Firestore listeners
cache.delete(f"expense:mega_bootstrap:{payer_id}")
```

#### 2. `settlement_service.py` - `_invalidate_settlement_cache()`
```python
# Phase 17.9: Only invalidate CREATOR's mega-bootstrap
# Receiver gets updates via Firestore balance listener
if creator_id:
    cache.delete(f"expense:mega_bootstrap:{creator_id}")
```

#### 3. `invitation_service.py` - `_invalidate_invitation_cache()`
```python
# Phase 17.9: Only invalidate INVITEE's mega-bootstrap
# Group members receive updates via Firestore invitation listener
# Invitee is NOT a member yet, so they need cache invalidation
invitee = user_repo.get_user_by_email(invitee_email)
if invitee:
    cache.delete(f"expense:mega_bootstrap:{invitee_id}")
```

#### 4. `group_service.py` - `_invalidate_membership_cache()`
```python
# Phase 17.9: Only invalidate ACTING user's mega-bootstrap
# Other members receive updates via Firestore listeners
cache.delete(f"expense:mega_bootstrap:{user_id}")
```

---

## Why This Works

### Firestore Real-Time Listeners Active
| Listener | Purpose | Users Covered |
|----------|---------|---------------|
| `listenToGroupExpenses` | Expense changes | All group members |
| `listenToUserBalances` | Balance updates | All users |
| `listenToGroupInvitations` | Invitation status | All group members |
| `listenToUserInvitations` | Pending invitations | Invitee |

### Cache Invalidation Now
| Event | Cache Invalidated For |
|-------|----------------------|
| Add expense | Payer only |
| Delete expense | Payer only |
| Create settlement | Creator only |
| Send invitation | Invitee only |
| Join/Leave group | Acting user only |

### Expected Impact
- Reduce `/user/groups` calls from 22 to ~2-4 per session
- Reduce `/mega-bootstrap` calls significantly
- Maintain real-time sync via Firestore listeners
- Faster UI response (no waiting for other users' cache invalidation)

---

## Testing Checklist

### Bug 1: Invitation Visibility
- [ ] User A sends invitation to User B
- [ ] User B sees invitation immediately (without refresh)
- [ ] Works with mixed-case emails

### Bug 2: Group Deletion
- [ ] Single click deletes group
- [ ] Navigation back to dashboard works
- [ ] No stale data appears

### Bug 3: Expense Deletion
- [ ] Delete expense updates balance correctly
- [ ] Expense remains in history (marked deleted)
- [ ] No "flash" of wrong values

### Phase 17.9: API Reduction
- [ ] Monitor `/user/groups` call count
- [ ] Monitor `/mega-bootstrap` call count
- [ ] Verify real-time sync still works between users

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `ExpenseManager.jsx` | Email normalization, delete retry logic, smart expense merge |
| `expense_service.py` | Selective cache invalidation (payer only) |
| `settlement_service.py` | Selective cache invalidation (creator only) |
| `invitation_service.py` | Selective cache invalidation (invitee only) |
| `group_service.py` | Selective cache invalidation (acting user only) |
