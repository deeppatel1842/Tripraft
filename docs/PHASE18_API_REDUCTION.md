# Phase 18: API Call Reduction

## Problem Statement
Session 4 API analysis showed **116 total API calls** in a single session:
- 33 GET `/api/expense/user/groups`
- 13 GET `/api/expense/mega-bootstrap`
- 48 OPTIONS preflight requests
- Plus various other endpoints

Target: Reduce to **<30 total API calls** per session.

## Root Cause Analysis
1. Firestore real-time listeners were calling `queryClient.invalidateQueries()` on every update.
   This triggered React Query to refetch data from the API, even though Firestore already had the latest data.
2. `groupMembershipMonitor` was polling `GET /user/groups` every **15 seconds** (hardcoded), causing 24+ unnecessary API calls.

## Implementation Status

### ✅ Phase 18.1: Reduce Polling Frequency
**File:** `web/frontend/src/utils/groupMembershipMonitor.js`
- Changed default polling interval from 15 seconds to 120 seconds
- ⚠️ Note: This was overridden by hardcoded 15s in ExpenseManager - fixed in Phase 18.7

### ✅ Phase 18.2: Disable Aggressive Refetch Triggers
**File:** `web/frontend/src/hooks/useExpenseQuery.js`
- Disabled `refetchOnWindowFocus` (was triggering on every tab switch)
- Disabled `refetchOnMount` (was triggering on component mount)
- Disabled `refetchOnReconnect` (was triggering on network reconnect)

### ✅ Phase 18.3: Increase staleTime
**File:** `web/frontend/src/hooks/useExpenseQuery.js`
- Increased `staleTime` from 5 minutes to 10 minutes
- Prevents React Query from marking data as stale too quickly

### ⏸ Phase 18.4: OPTIONS Preflight Caching (Not Implemented)
- Could add `Access-Control-Max-Age` header to cache CORS preflight
- Lower priority since main issue was resolved

### ✅ Phase 18.5: Request Deduplication
**File:** `web/frontend/src/services/expenseApi.js`
- Added `pendingRequests` Map to track in-flight requests
- `deduplicateRequest()` prevents parallel duplicate API calls
- Applied to `getUserGroups()` and `getMegaBootstrap()`

### ✅ Phase 18.6: Firestore Listener Optimization (ROOT CAUSE FIX)
**File:** `web/frontend/src/components/expenses/ExpenseManager.jsx`

**Problem:** Firestore listeners were calling `invalidateQueries()` which triggers API refetch cascade.

**Solution:** Replace `invalidateQueries()` with `setQueryData()` for direct cache updates.

| Listener | Status | Description |
|----------|--------|-------------|
| `listenToUserExpenseGroups` | ✅ Fixed | Uses setQueryData for groups cache |
| `listenToGroupMembers` | ✅ Fixed | Uses setQueryData for megaBootstrap + group cache |
| `listenToGroupInvitations` | ✅ Fixed | Uses setQueryData for `invitations` field |
| `listenToUserInvitations` | ✅ Fixed | Updates both megaBootstrap and invitations caches |
| `listenToGroupExpenses` | ✅ Already correct | Uses setQueryData |
| `listenToGroupBalances` | ✅ Already correct | Uses setQueryData |
| `listenToGroupSettlements` | ✅ Already correct | Uses setQueryData |

### ✅ Phase 18.7: Disable groupMembershipMonitor Polling (MAJOR FIX)
**File:** `web/frontend/src/components/expenses/ExpenseManager.jsx`

**Problem:** `groupMembershipMonitor.startMonitoring()` was called with hardcoded `15000ms` (15s) interval.
This caused **24+ GET /user/groups API calls** every few minutes!

**Solution:** Completely disabled API polling. Firestore real-time listeners now handle all membership detection:
- `GroupPlannerContext.listenToUserGroups` - detects when user's group list changes
- `ExpenseManager.listenToGroupMembers` - detects member changes within active group

**Result:** Eliminated 24+ unnecessary API calls per session.

**Remaining intentional invalidateQueries calls (user-initiated):**
- `reloadActiveGroup()` - explicit refresh with cache bypass
- `onRefreshInvitations` - user clicks refresh button
- `onInvitationAccepted` - user accepts invitation

## Results

### Before Phase 18
| Count | Endpoint |
|-------|----------|
| 33 | GET /api/expense/user/groups |
| 13 | GET /api/expense/mega-bootstrap |
| 48 | OPTIONS preflight |
| **116** | **Total** |

### After Phase 18.7
| Count | Endpoint |
|-------|----------|
| 2-3 | GET /api/expense/mega-bootstrap (initial load only) |
| 1-2 | POST /api/expense/expenses (per expense created) |
| 1 | POST /api/expense/settlements (per settlement) |
| 0 | GET /api/expense/user/groups (eliminated!) |
| **<15** | **Expected Total per session** |

## Bug Fixes Included in Phase 18

1. **Member display name showing "C V"** - Fixed Firestore member listener to merge user details
2. **User B not seeing invitations** - Fixed invitations listener to update both caches
3. **User B's balance not showing** - Fixed optimistic update to create new balance entries
4. **Accepted invitation still pending** - Fixed listener to update correct `invitations` field
5. **Removed member showing "Unknown"** - Fixed to preserve members in `all_members_map`
6. **Group deletion two clicks** - Fixed to use context's optimistic delete
7. **Group deletion 403 error** - Made backend `delete_group` idempotent

## Date Completed
December 3, 2025
