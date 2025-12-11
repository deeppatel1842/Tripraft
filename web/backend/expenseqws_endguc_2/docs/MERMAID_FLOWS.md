# 🔄 Mermaid Flowcharts - Individual Flows

This document contains detailed Mermaid flowcharts for each major operation in the Expense Engine.

---

## 📋 Table of Contents

1. [User Authentication Flow](#1-user-authentication-flow)
2. [Create Group Flow](#2-create-group-flow)
3. [Send Invitation Flow](#3-send-invitation-flow)
4. [Accept Invitation Flow](#4-accept-invitation-flow)
5. [Load Group Data Flow](#5-load-group-data-flow)
6. [Create Expense Flow](#6-create-expense-flow)
7. [Update Expense Flow](#7-update-expense-flow)
8. [Delete Expense Flow](#8-delete-expense-flow)
9. [Calculate Balances Flow](#9-calculate-balances-flow)
10. [Create Settlement Flow](#10-create-settlement-flow)
11. [Delete Group Flow](#11-delete-group-flow)
12. [Cache Invalidation Flow](#12-cache-invalidation-flow)

---

## 1. User Authentication Flow

### Timing: 800ms (first time), 50ms (cached token)

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FB_UI as Firebase Auth UI
    participant FB_AUTH as Firebase Auth Backend
    participant API as Expense Backend
    participant FS as Firestore
    
    Note over U,FS: New User Registration
    
    U->>FB_UI: Fill registration form<br/>(email, password, name)
    FB_UI->>FB_AUTH: Create account
    FB_AUTH->>FB_AUTH: Validate password strength<br/>Check if email exists
    FB_AUTH-->>FB_UI: Account created<br/>Return JWT token (valid 1 hour)
    FB_UI->>U: Store token in localStorage
    
    Note over U,API: Create Expense Profile
    
    U->>API: POST /api/expense/user/profile<br/>Bearer: JWT_TOKEN
    
    API->>API: Extract & verify JWT signature
    API->>FB_AUTH: Verify token with Firebase
    FB_AUTH-->>API: Token valid ✅<br/>User ID: USER123
    
    API->>FS: Create user profile document
    Note over FS: Collection: users<br/>Document: USER123<br/>{display_name, email, username}
    FS-->>API: Profile created (150ms)
    
    API->>API: Generate unique username<br/>(if not provided)
    API-->>U: Return profile (200ms total)
    
    Note over U,API: Subsequent Requests (Token Cached)
    
    U->>API: GET /api/expense/groups<br/>Bearer: JWT_TOKEN
    API->>API: Verify JWT signature locally
    Note over API: Token already validated<br/>Extract user ID from claims
    API->>FS: Fetch user's groups
    FS-->>API: Return groups (50ms)
    API-->>U: Return data (55ms total)
    
    Note over U: Token valid for 1 hour<br/>Auto-refreshed by Firebase SDK
```

**Key Points:**
- First auth: 800ms (account creation + profile)
- Subsequent requests: 50-100ms (JWT verification only)
- Token auto-refreshes before expiry
- No need to re-login every hour

---

## 2. Create Group Flow

### Timing: 250ms

```mermaid
sequenceDiagram
    participant U as User Browser
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant REDIS as Redis Cache
    participant BAL as Balance Manager
    
    Note over U,BAL: User clicks "Create New Group"
    
    U->>RQ: Submit group form<br/>{name, description, currency}
    RQ->>API: POST /api/expense/groups
    
    Note over API: Validate request
    API->>API: Check required fields<br/>Validate currency code<br/>Authenticate user
    
    Note over API,FS: Create group in Firestore
    
    API->>FS: Start transaction
    FS->>FS: Create group document
    Note over FS: Collection: groups<br/>Document: GROUP123<br/>{name, created_by, currency}
    
    FS->>FS: Create members subcollection
    Note over FS: Add creator as owner<br/>role: "owner"<br/>permissions: ALL
    
    FS-->>API: Transaction committed (150ms)
    
    Note over API,BAL: Initialize balance document
    
    API->>BAL: Create balance document
    BAL->>FS: Write empty balance doc
    Note over FS: Collection: balances<br/>Document: GROUP123<br/>{member_balances: {USER123: 0.00}}
    FS-->>BAL: Balance doc created (50ms)
    
    Note over API,REDIS: Cache creator's data
    
    API->>REDIS: Cache group details
    REDIS->>REDIS: SET group_full:GROUP123<br/>TTL: 30 minutes
    
    API->>REDIS: Invalidate user's group list
    REDIS->>REDIS: DELETE user_groups:USER123<br/>DELETE user_groups:USER123_summary
    
    API-->>RQ: Return group data (250ms total)
    Note over RQ: {group_id, name, members: [creator],<br/>member_count: 1, balances: {}}
    
    RQ->>RQ: Invalidate groups query<br/>Trigger refetch
    RQ-->>U: Show success message<br/>"Group created!"
    
    U->>U: Redirect to group page
```

**Key Points:**
- Total time: 250ms
- Firestore transaction ensures consistency
- Balance document initialized immediately
- Creator added as owner automatically
- Cache invalidated for fresh data on next load

---

## 3. Send Invitation Flow

### Timing: 300ms (includes email sending)

```mermaid
sequenceDiagram
    participant U as Owner
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant REDIS as Redis Cache
    participant EMAIL as Email Worker
    
    Note over U,EMAIL: Owner invites friend to group
    
    U->>RQ: Enter email: friend@example.com<br/>Click "Send Invitation"
    RQ->>API: POST /api/expense/invitations<br/>{group_id, invited_email, role}
    
    Note over API: Validate invitation
    
    API->>REDIS: GET group_members:GROUP123
    alt Cache HIT
        REDIS-->>API: Member list (2ms)
    else Cache MISS
        API->>FS: Get group members
        FS-->>API: Member list (60ms)
    end
    
    API->>API: Check validations:<br/>✓ Sender is group member<br/>✓ Email not already a member<br/>✓ Group not at max capacity (50)
    
    Note over API,FS: Create invitation
    
    API->>FS: Write invitation document
    Note over FS: Collection: invitations<br/>Document: INV123<br/>{group_id, invited_by, invited_email,<br/>status: "pending", expires_at: +7 days}
    FS-->>API: Invitation created (120ms)
    
    Note over API: Generate shareable link
    API->>API: Create invitation link<br/>https://app.com/invite/INV123
    
    Note over API,EMAIL: Send email (async)
    
    API->>EMAIL: Queue email notification
    Note over EMAIL: Background task starts
    
    EMAIL->>EMAIL: Render email template
    Note over EMAIL: Subject: "John invited you to<br/>Apartment Roommates"<br/>Body: Invitation details + link
    
    EMAIL->>EMAIL: Send via SMTP
    Note over EMAIL: To: friend@example.com<br/>From: noreply@app.com
    
    Note over API: Don't wait for email!
    
    API-->>RQ: Return invitation (250ms)
    Note over RQ: {invitation_id, share_link,<br/>expires_at, email_sent: true}
    
    RQ-->>U: Show success<br/>"Invitation sent to friend@example.com"
    
    Note over EMAIL: Email sending completes
    EMAIL->>EMAIL: Log result (success/failure)
    
    Note over U: If email fails, user can<br/>share link manually
```

**Key Points:**
- Total response: 250ms (email sent async)
- Email doesn't delay API response
- Shareable link as backup if email fails
- Invitation expires in 7 days
- Owner can resend if needed

---

## 4. Accept Invitation Flow

### Timing: 220ms

```mermaid
sequenceDiagram
    participant JANE as Jane (Invitee)
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant REDIS as Redis Cache
    participant BAL as Balance Manager
    
    Note over JANE,BAL: Jane clicks invitation link or "Accept" button
    
    JANE->>RQ: Click "Accept Invitation"
    RQ->>API: POST /invitations/INV123/accept
    
    Note over API: Validate invitation
    
    API->>FS: Get invitation document
    FS-->>API: Invitation data (80ms)
    
    API->>API: Check validations:<br/>✓ Status = "pending"<br/>✓ Not expired (< 7 days)<br/>✓ Jane is the invited user<br/>✓ Jane not already member
    
    Note over API,FS: Atomic group join
    
    API->>FS: Start Firestore transaction
    
    par Parallel Transaction Operations
        FS->>FS: Update invitation<br/>status: "accepted"<br/>accepted_at: now
        
        FS->>FS: Add Jane to members<br/>role: "member"<br/>joined_at: now
        
        FS->>FS: Increment group.member_count += 1
    end
    
    FS-->>API: Transaction committed (120ms)
    
    Note over API,BAL: Initialize Jane's balance
    
    API->>BAL: Add member to balances
    BAL->>FS: Get balance document
    FS-->>BAL: Current balances (30ms)
    
    BAL->>BAL: Add Jane with $0.00 balance
    BAL->>FS: Update balance document
    FS-->>BAL: Updated (40ms)
    
    Note over API,REDIS: MASSIVE cache invalidation
    
    par Invalidate Jane's Caches
        REDIS->>REDIS: DEL invitations:enriched:JANE*<br/>(wildcard - all pagination)
        REDIS->>REDIS: DEL user_groups:JANE
        REDIS->>REDIS: DEL user_groups:JANE_summary
    end
    
    par Invalidate Group Caches
        REDIS->>REDIS: DEL group_full:GROUP123
        REDIS->>REDIS: DEL group_balance_formatted:GROUP123
    end
    
    par Invalidate All Member Caches
        loop For each existing member
            REDIS->>REDIS: DEL user_groups:MEMBER_ID
            REDIS->>REDIS: DEL user_groups:MEMBER_ID_summary
        end
    end
    
    Note over REDIS: Total: 15-20 cache keys deleted (10ms)
    
    API-->>RQ: Success (220ms total)
    Note over RQ: {group_id, group_name, role: "member"}
    
    RQ->>RQ: Invalidate queries:<br/>- invitations<br/>- groups<br/>- group details
    
    RQ->>API: Fetch fresh data
    Note over RQ: All caches cleared,<br/>so fetches from Firestore
    
    API->>FS: Get updated group + invitations
    FS-->>API: Fresh data (150ms)
    API-->>RQ: Return
    
    RQ-->>JANE: Redirect to group page<br/>"Welcome to Apartment Roommates!"
    
    Note over JANE: Jane sees:<br/>- She's now a member<br/>- Current expenses<br/>- Her balance: $0.00
```

**Key Points:**
- Total time: 220ms
- Firestore transaction ensures atomic join
- 15-20 cache keys invalidated (all members affected)
- Wildcard deletion for pagination variants
- All members see Jane as member on next request

---

## 5. Load Group Data Flow

### Timing: 5ms (cached) or 200ms (cold)

```mermaid
sequenceDiagram
    participant U as User Browser
    participant RQ as React Query
    participant API as Flask Backend
    participant REDIS as Redis Cache
    participant FS as Firestore
    
    Note over U,FS: User clicks "Apartment Roommates" group
    
    U->>RQ: Request group data
    
    Note over RQ: Check React Query cache
    
    alt React Query Cache HIT (data < 30s old)
        RQ-->>U: Return instantly (0ms) ⚡
        Note over U: Display data from memory<br/>No API call needed
        
        Note over RQ: Background refetch
        RQ->>API: GET /groups/GROUP123/full<br/>(silent background check)
        Note over API: This happens AFTER user sees data
        
        API->>REDIS: GET group_full:GROUP123
        REDIS-->>API: Latest data (3ms)
        API-->>RQ: Update cache silently
        Note over RQ: If data changed, UI updates<br/>If same, no change
        
    else React Query Cache MISS or stale
        RQ->>API: GET /api/expense/groups/GROUP123/full
        
        Note over API: Authenticate JWT
        API->>API: Verify token<br/>Check user is member
        
        API->>REDIS: GET group_full:GROUP123
        
        alt Redis Cache HIT (95% of requests)
            REDIS-->>API: Complete data (3ms) ⚡
            Note over REDIS: Includes:<br/>- Group details<br/>- All members<br/>- Recent expenses (50)<br/>- Current balances<br/>- Display names
            
            API-->>RQ: Return JSON (5ms total)
            RQ-->>U: Display data
            
        else Redis Cache MISS (5% - cold start)
            REDIS-->>API: Key not found
            
            Note over API,FS: Batch fetch optimization
            
            par Parallel Firestore Queries
                API->>FS: Get group document
                FS-->>API: Group details (50ms)
                
                API->>FS: Get members subcollection
                FS-->>API: Member list (60ms)
                
                API->>FS: Get expenses (last 50)
                FS-->>API: Expense list (80ms)
                
                API->>FS: Get balance document
                FS-->>API: Balances (40ms)
            end
            
            Note over API: Wait for slowest query<br/>Total: 80ms
            
            Note over API: Batch fetch display names
            API->>REDIS: MGET display_name:USER1<br/>display_name:USER2<br/>display_name:USER3...
            
            alt Display names cached
                REDIS-->>API: All names (1ms)
            else Some names missing
                REDIS-->>API: Partial names
                API->>FS: Get missing usernames
                FS-->>API: Usernames (40ms)
                API->>REDIS: Cache new names
            end
            
            Note over API: Combine all data
            API->>API: Transform & enrich:<br/>- Add display names<br/>- Calculate summaries<br/>- Format dates<br/>(20ms processing)
            
            Note over API,REDIS: Cache complete response
            API->>REDIS: SET group_full:GROUP123<br/>Value: Complete JSON<br/>TTL: 1800s (30 min)
            REDIS-->>API: OK (1ms)
            
            API-->>RQ: Return JSON (200ms total)
            RQ-->>U: Display data
        end
    end
    
    Note over U: User sees:<br/>✓ Group name & details<br/>✓ All members with names<br/>✓ Recent 50 expenses<br/>✓ Current balance: -$45.50<br/>✓ Who owes what
```

**Performance Breakdown:**
- **Browser cache HIT:** 0ms (instant)
- **Redis cache HIT:** 5ms (95% of requests)
- **Cold start:** 200ms (5% of requests)

**Cache Strategy:**
- React Query: 30s stale time
- Redis: 30 min TTL
- Background refetch ensures freshness

---

## 6. Create Expense Flow

### Timing: 200ms (user sees 0ms due to optimistic update)

```mermaid
sequenceDiagram
    participant U as User
    participant RQ as React Query
    participant API as Flask Backend
    participant IDEM as Idempotency Mgr
    participant FS as Firestore
    participant BAL as Balance Manager
    participant REDIS as Redis Cache
    participant EMAIL as Email Worker
    
    Note over U,EMAIL: John adds $120 dinner expense split 3 ways
    
    U->>RQ: Submit expense form<br/>{amount: 120, paid_by: John,<br/>split: [John, Jane, Bob]}
    
    Note over RQ: OPTIMISTIC UPDATE
    RQ->>RQ: Calculate split: $40 each
    RQ->>RQ: Add expense to local cache
    RQ-->>U: Show expense INSTANTLY (0ms) ⚡
    Note over U: Expense appears with<br/>"pending" indicator
    
    Note over RQ: Background: Send request
    RQ->>API: POST /api/expense/expenses
    
    Note over API: Generate idempotency key
    API->>API: UUID: expense-uuid-12345
    
    API->>IDEM: Check duplicate
    IDEM->>REDIS: GET idempotency:expense-uuid-12345
    
    alt Duplicate Request (network retry)
        REDIS-->>IDEM: Key exists with expense_id
        IDEM-->>API: Return existing expense
        API-->>RQ: Expense already created
        RQ-->>U: Remove "pending" (no change)
        
    else New Request
        REDIS-->>IDEM: Key not found
        IDEM->>REDIS: SET idempotency:expense-uuid-12345<br/>TTL: 24 hours
        
        Note over API: Validate request
        API->>API: Check:<br/>✓ Splits sum = amount<br/>✓ All users are members<br/>✓ Amount > 0<br/>✓ Valid split type
        
        Note over API,FS: Write expense
        
        API->>FS: Start transaction
        
        par Create Expense Documents
            FS->>FS: Write expense document
            Note over FS: expense_id: EXP123<br/>amount: $120<br/>paid_by: John
            
            FS->>FS: Write split documents (3)
            Note over FS: John: $40<br/>Jane: $40<br/>Bob: $40
        end
        
        FS-->>API: Transaction committed (150ms)
        
        Note over API,BAL: Update balances incrementally
        
        API->>BAL: Update balances
        BAL->>FS: Get balance document
        FS-->>BAL: Current balances (30ms)
        
        Note over BAL: Incremental calculation:<br/>NO full recalc from expenses!
        
        BAL->>BAL: Apply changes:<br/>John: +$80 (paid $120, owes $40)<br/>Jane: -$40 (owes)<br/>Bob: -$40 (owes)
        
        BAL->>FS: Update balance document
        FS-->>BAL: Updated (40ms)
        
        Note over API,REDIS: Invalidate caches for ALL members
        
        par Cache Invalidation (Parallel)
            REDIS->>REDIS: DEL user_groups:JOHN*
            REDIS->>REDIS: DEL user_groups:JANE*
            REDIS->>REDIS: DEL user_groups:BOB*
            REDIS->>REDIS: DEL group_full:GROUP123
            REDIS->>REDIS: DEL group_balance_formatted:GROUP123
            REDIS->>REDIS: DEL expenses:group:GROUP123*
        end
        
        Note over REDIS: 10+ keys deleted (5ms)
        
        Note over API: Prepare response
        API->>REDIS: MGET display names
        REDIS-->>API: Names (1ms)
        
        API->>API: Enrich expense:<br/>- Add display names<br/>- Calculate net effects<br/>- Format response
        
        API-->>RQ: Return expense (200ms total)
        Note over RQ: {expense_id: EXP123,<br/>balances_updated: true,<br/>notifications_queued: true}
        
        RQ->>RQ: Replace optimistic data
        RQ-->>U: Remove "pending" ✓<br/>Show real expense
        
        Note over U: Balances update:<br/>John: $50 → $130 (+$80)<br/>Jane: -$20 → -$60 (-$40)<br/>Bob: -$30 → -$70 (-$40)
        
        Note over API,EMAIL: Send emails (async)
        
        API->>EMAIL: Queue notifications
        
        par Email Notifications (Background)
            EMAIL->>EMAIL: Send to Jane<br/>"John added $120 dinner,<br/>you owe $40"
            
            EMAIL->>EMAIL: Send to Bob<br/>"John added $120 dinner,<br/>you owe $40"
        end
        
        Note over EMAIL: Emails sent in background<br/>Don't delay API response
    end
    
    Note over RQ: Trigger refetch
    RQ->>API: GET /groups/GROUP123/full
    Note over RQ: Fetch fresh data to confirm
    API->>FS: Get latest (cache was invalidated)
    FS-->>API: Fresh group data
    API-->>RQ: Return
    RQ-->>U: UI confirms update
```

**User Experience Timeline:**
- **0ms:** User submits form
- **0ms:** Expense appears (optimistic)
- **200ms:** Server confirms creation
- **200ms:** "Pending" indicator removed
- **Background:** Emails sent (no delay)

**Why So Fast for User:**
- Optimistic update = instant feedback
- User doesn't wait for server
- Confirmation happens in background

---

## 7. Update Expense Flow

### Timing: 280ms

```mermaid
sequenceDiagram
    participant U as User
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant BAL as Balance Manager
    participant REDIS as Redis Cache
    
    Note over U,REDIS: User edits expense: $120 → $150
    
    U->>RQ: Update expense form<br/>Old: $120 split 3 ways<br/>New: $150 split 3 ways
    
    Note over RQ: Calculate optimistic balances
    RQ->>RQ: Old splits: $40 each<br/>New splits: $50 each<br/>Difference: +$10 each
    
    RQ->>RQ: Update local cache:<br/>John: +$10 net effect<br/>Jane: -$10 more owed<br/>Bob: -$10 more owed
    
    RQ-->>U: Show updated expense instantly (0ms)
    Note over U: Sees new amount $150<br/>with "saving..." indicator
    
    RQ->>API: PUT /api/expense/expenses/EXP123
    
    Note over API: Validate update
    API->>API: Check:<br/>✓ User is creator or admin<br/>✓ New splits valid<br/>✓ Amount > 0
    
    API->>FS: Get old expense data
    FS-->>API: Old expense (60ms)
    Note over API: Store old values for<br/>balance reversal
    
    Note over API,FS: Update expense
    
    API->>FS: Update expense document
    Note over FS: amount: $120 → $150<br/>updated_at: now<br/>updated_by: USER
    FS-->>API: Updated (100ms)
    
    Note over API,BAL: Adjust balances incrementally
    
    API->>BAL: Adjust balances
    Note over BAL: Smart calculation:<br/>1. Reverse old balance impact<br/>2. Apply new balance impact
    
    BAL->>FS: Get balance document
    FS-->>BAL: Current balances (30ms)
    
    BAL->>BAL: Reverse old expense:<br/>John: -$80 (paid $120, owed $40)<br/>Jane: +$40<br/>Bob: +$40
    
    BAL->>BAL: Apply new expense:<br/>John: +$100 (paid $150, owes $50)<br/>Jane: -$50<br/>Bob: -$50
    
    BAL->>BAL: Net changes:<br/>John: +$20 total<br/>Jane: -$10 total<br/>Bob: -$10 total
    
    BAL->>FS: Update balance document
    FS-->>BAL: Updated (50ms)
    
    Note over API,REDIS: Invalidate caches
    
    par Cache Invalidation
        REDIS->>REDIS: DEL user_groups:* (all 3 members)
        REDIS->>REDIS: DEL group_full:GROUP123
        REDIS->>REDIS: DEL group_balance_formatted:GROUP123
        REDIS->>REDIS: DEL expenses:group:GROUP123*
    end
    
    API-->>RQ: Return updated expense (280ms)
    Note over RQ: {expense_id, new_amount: $150,<br/>balance_adjustment: +$30 total}
    
    RQ->>RQ: Replace optimistic data
    RQ-->>U: Remove "saving..." ✓<br/>Show confirmed update
    
    Note over U: Final balances:<br/>John: $130 → $150 (+$20)<br/>Jane: -$60 → -$70 (-$10)<br/>Bob: -$70 → -$80 (-$10)
```

**Key Points:**
- Old expense impact reversed first
- New expense impact applied
- Net change calculated automatically
- User sees instant feedback (optimistic)
- Server confirms in 280ms

---

## 8. Delete Expense Flow

### Timing: 220ms

```mermaid
sequenceDiagram
    participant U as User
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant BAL as Balance Manager
    participant REDIS as Redis Cache
    
    Note over U,REDIS: User deletes $120 expense
    
    U->>RQ: Click "Delete Expense"<br/>Confirm deletion
    
    Note over RQ: Optimistic removal
    RQ->>RQ: Calculate reverse balance:<br/>John: -$80<br/>Jane: +$40<br/>Bob: +$40
    
    RQ->>RQ: Remove expense from list
    RQ-->>U: Expense disappears (0ms)
    Note over U: Sees "deleting..." indicator
    
    RQ->>API: DELETE /api/expense/expenses/EXP123
    
    Note over API: Validate deletion
    API->>API: Check:<br/>✓ User is creator or admin<br/>✓ Expense exists<br/>✓ Group still exists
    
    API->>FS: Get expense data
    FS-->>API: Expense details (60ms)
    Note over API: Need details to reverse balances
    
    Note over API,BAL: Revert balance changes
    
    API->>BAL: Revert expense
    BAL->>FS: Get balance document
    FS-->>BAL: Current balances (30ms)
    
    BAL->>BAL: Reverse expense impact:<br/>John: -$80 (remove credit)<br/>Jane: +$40 (remove debt)<br/>Bob: +$40 (remove debt)
    
    BAL->>FS: Update balance document
    FS-->>BAL: Updated (40ms)
    
    Note over API,FS: Delete expense
    
    API->>FS: Delete expense document
    API->>FS: Delete split documents
    FS-->>API: Deleted (80ms)
    
    Note over API,REDIS: Invalidate caches
    
    par Cache Invalidation
        REDIS->>REDIS: DEL user_groups:* (all members)
        REDIS->>REDIS: DEL group_full:GROUP123
        REDIS->>REDIS: DEL group_balance_formatted:GROUP123
        REDIS->>REDIS: DEL expenses:group:GROUP123*
    end
    
    Note over API: Log deletion in audit trail
    API->>FS: Write audit log
    Note over FS: {action: "expense_deleted",<br/>expense_id, by_uid, timestamp}
    
    API-->>RQ: Deletion confirmed (220ms)
    Note over RQ: {success: true,<br/>balance_reverted: true}
    
    RQ->>RQ: Confirm removal from cache
    RQ-->>U: Remove "deleting..." ✓
    
    Note over U: Final balances:<br/>John: $130 → $50 (-$80)<br/>Jane: -$60 → -$20 (+$40)<br/>Bob: -$70 → -$30 (+$40)
```

**Key Points:**
- Expense data fetched before deletion (needed for balance reversal)
- Balances reverted before document deletion
- Audit log created for compliance
- Cannot be undone (permanent deletion)

---

## 9. Calculate Balances Flow

### Timing: 2ms (cached) or 60ms (cold)

```mermaid
sequenceDiagram
    participant U as User
    participant RQ as React Query
    participant API as Flask Backend
    participant REDIS as Redis Cache
    participant FS as Firestore
    participant BAL as Balance Manager
    
    Note over U,BAL: User clicks "Balances" tab
    
    U->>RQ: Request balances
    RQ->>API: GET /api/expense/balance/group/GROUP123
    
    Note over API: Check formatted cache first
    
    API->>REDIS: GET group_balance_formatted:GROUP123
    
    alt Formatted Cache HIT (89% of requests)
        REDIS-->>API: Pre-formatted JSON (1ms) ⚡
        Note over REDIS: Includes:<br/>- Member balances<br/>- Simplified debts<br/>- Settlement suggestions<br/>- Summary stats<br/>- Display names
        
        API-->>RQ: Return balances (2ms total)
        RQ-->>U: Display balance UI
        
    else Formatted Cache MISS
        REDIS-->>API: Key not found
        
        Note over API,BAL: Get raw balances
        
        API->>BAL: Get group balances
        BAL->>FS: Get balance document
        FS-->>BAL: Raw balance data (40ms)
        
        Note over BAL: Raw data:<br/>John: +$85.50<br/>Jane: -$45.50<br/>Bob: -$40.00<br/>Alice: $0.00
        
        Note over BAL: Apply debt simplification
        
        BAL->>BAL: Step 1: Separate creditors & debtors
        Note over BAL: Creditors (positive):<br/>John: +$85.50<br/><br/>Debtors (negative):<br/>Jane: -$45.50<br/>Bob: -$40.00
        
        BAL->>BAL: Step 2: Sort by amount
        Note over BAL: Largest creditor: John ($85.50)<br/>Largest debtor: Jane ($45.50)
        
        BAL->>BAL: Step 3: Match & simplify
        Note over BAL: Jane pays John: $45.50<br/>John remaining: $40.00<br/><br/>Bob pays John: $40.00<br/>John remaining: $0.00<br/><br/>Result: 2 transactions<br/>(instead of potentially 6)
        
        BAL-->>API: Simplified debts
        Note over API: [{from: Jane, to: John, amount: 45.50},<br/>{from: Bob, to: John, amount: 40.00}]
        
        Note over API: Batch fetch display names
        
        API->>REDIS: MGET display_name:JOHN<br/>display_name:JANE<br/>display_name:BOB
        REDIS-->>API: All names (1ms)
        
        Note over API: Format complete response
        
        API->>API: Build JSON:<br/>- Member balances with names<br/>- Simplified debts with names<br/>- Settlement suggestions<br/>- Summary statistics
        
        Note over API,REDIS: Cache formatted response
        
        API->>REDIS: SET group_balance_formatted:GROUP123<br/>TTL: 300s (5 minutes)
        REDIS-->>API: OK (1ms)
        
        API-->>RQ: Return formatted balances (60ms)
        RQ-->>U: Display balance UI
    end
    
    Note over U: User sees:<br/>💰 Who owes what<br/>📊 Simplified settlements<br/>💡 Payment suggestions
```

**Response Example:**
```json
{
  "balances": [
    {"uid": "john", "name": "John Doe", "balance": 85.50},
    {"uid": "jane", "name": "Jane Smith", "balance": -45.50},
    {"uid": "bob", "name": "Bob", "balance": -40.00}
  ],
  "simplified_debts": [
    {
      "from_uid": "jane",
      "from_name": "Jane Smith",
      "to_uid": "john",
      "to_name": "John Doe",
      "amount": 45.50,
      "suggestion": "Jane pays John $45.50"
    },
    {
      "from_uid": "bob",
      "from_name": "Bob",
      "to_uid": "john",
      "to_name": "John Doe",
      "amount": 40.00,
      "suggestion": "Bob pays John $40.00"
    }
  ],
  "summary": {
    "total_expenses": 1250.75,
    "settled_amount": 500.00,
    "outstanding": 750.75
  }
}
```

**Performance Notes:**
- Formatted cache: 2ms (89% hit rate)
- Raw balance + formatting: 60ms
- Cache TTL: 5 minutes (frequent changes)
- Invalidated on: New expense, settlement

---

## 10. Create Settlement Flow

### Timing: 200ms

```mermaid
sequenceDiagram
    participant JANE as Jane (Payer)
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant BAL as Balance Manager
    participant REDIS as Redis Cache
    
    Note over JANE,REDIS: Jane settles debt with John: $45.50
    
    JANE->>RQ: Record payment<br/>{from: Jane, to: John,<br/>amount: $45.50, method: Venmo}
    
    RQ->>RQ: Calculate optimistic balance:<br/>Jane: -$45.50 → $0.00<br/>John: +$85.50 → +$40.00
    
    RQ->>RQ: Add settlement to list
    RQ-->>JANE: Show payment recorded (0ms)
    Note over JANE: Sees "recording..." indicator
    
    RQ->>API: POST /api/expense/settlements
    
    Note over API: Validate settlement
    
    API->>API: Check:<br/>✓ Both users in same group<br/>✓ Amount > 0<br/>✓ Payment method valid
    
    Note over API: Get current balances for validation
    
    API->>BAL: Get balances (force fresh)
    BAL->>FS: Get balance document<br/>(bypass cache)
    FS-->>BAL: Current balances (40ms)
    
    API->>API: Validate debt exists:<br/>Jane owes John: $45.50 ✓<br/>Settlement amount: $45.50 ✓<br/>(Warning if amount > debt)
    
    Note over API,FS: Record settlement
    
    API->>FS: Write settlement document
    Note over FS: Collection: settlements<br/>Document: SETTLE123<br/>{from: Jane, to: John,<br/>amount: $45.50, method: Venmo,<br/>payment_date: now}
    FS-->>API: Settlement created (100ms)
    
    Note over API,BAL: Update balances
    
    API->>BAL: Apply settlement
    BAL->>BAL: Calculate changes:<br/>Jane: +$45.50 (reduces debt)<br/>John: -$45.50 (receives payment)
    
    BAL->>FS: Update balance document
    Note over FS: Jane: -$45.50 → $0.00<br/>John: +$85.50 → +$40.00
    FS-->>BAL: Updated (50ms)
    
    Note over API,REDIS: Invalidate caches
    
    par Cache Invalidation
        REDIS->>REDIS: DEL user_groups:JANE*
        REDIS->>REDIS: DEL user_groups:JOHN*
        REDIS->>REDIS: DEL group_balance_formatted:GROUP123
        REDIS->>REDIS: DEL settlements:group:GROUP123*
    end
    
    API-->>RQ: Settlement confirmed (200ms)
    Note over RQ: {settlement_id,<br/>new_balances: {jane: 0, john: 40}}
    
    RQ->>RQ: Replace optimistic data
    RQ-->>JANE: Remove "recording..." ✓<br/>Show confirmed payment
    
    Note over JANE: Balances updated:<br/>Jane: $0.00 (settled!)<br/>John: $40.00 (still owed by Bob)
    
    Note over JANE: Settlement appears in history
```

**Key Points:**
- Validates debt exists before recording
- Warns if amount exceeds debt (doesn't block)
- Balances update immediately
- Settlement history shows payment
- Cannot be deleted (audit trail)

---

## 11. Delete Group Flow

### Timing: 550ms

```mermaid
sequenceDiagram
    participant OWNER as Group Owner
    participant RQ as React Query
    participant API as Flask Backend
    participant FS as Firestore
    participant REDIS as Redis Cache
    
    Note over OWNER,REDIS: Owner deletes "Europe Trip" group (6 members)
    
    OWNER->>RQ: Click "Delete Group"<br/>Confirm with password
    
    RQ->>RQ: Remove group from local cache
    RQ-->>OWNER: Show "deleting..." (0ms)
    
    RQ->>API: DELETE /api/expense/groups/GROUP123
    
    Note over API: Validate deletion permissions
    
    API->>API: Check:<br/>✓ User is group owner<br/>✓ Group exists
    
    API->>FS: Get group with members
    FS-->>API: Group data + 6 members (50ms)
    
    Note over API: Check if all balances settled
    
    API->>FS: Get balance document
    FS-->>API: Balances (40ms)
    
    API->>API: Validate all balances = $0.00
    
    alt Unsettled Balances Exist
        API-->>RQ: Error 400<br/>"Cannot delete with unsettled balances"
        RQ-->>OWNER: Show error message<br/>with balance details
        OWNER->>OWNER: Must settle balances first<br/>or use "force delete"
        
    else All Balances Settled
        Note over API,FS: CASCADE DELETION
        
        API->>FS: Start batch delete
        
        par Delete All Related Documents
            FS->>FS: Delete group document
            
            FS->>FS: Delete 25 expense documents
            
            FS->>FS: Delete 3 expense splits each<br/>(75 split documents)
            
            FS->>FS: Delete 8 settlement documents
            
            FS->>FS: Delete 3 invitation documents
            
            FS->>FS: Delete balance document
            
            FS->>FS: Delete members subcollection<br/>(6 member documents)
        end
        
        FS-->>API: All deleted (400ms)
        Note over FS: Total: 118 documents deleted!
        
        Note over API,REDIS: MASSIVE cache invalidation
        
        Note over REDIS: Must invalidate for ALL 6 members
        
        par Invalidate Member Caches (6 members)
            loop For each of 6 members
                REDIS->>REDIS: DEL user_groups:MEMBER_ID
                REDIS->>REDIS: DEL user_groups:MEMBER_ID_summary
            end
        end
        
        par Invalidate Group Caches
            REDIS->>REDIS: DEL group_full:GROUP123
            REDIS->>REDIS: DEL group_balance_formatted:GROUP123
            REDIS->>REDIS: DEL expenses:group:GROUP123*
            REDIS->>REDIS: DEL settlements:group:GROUP123*
            REDIS->>REDIS: DEL invitations:group:GROUP123*
            REDIS->>REDIS: DEL group_members:GROUP123
        end
        
        Note over REDIS: 25+ cache keys deleted (10ms)
        
        Note over API: Log deletion
        API->>FS: Write audit log
        Note over FS: {action: "group_deleted",<br/>group_id, by_uid: owner,<br/>timestamp, members_affected: 6,<br/>documents_deleted: 118}
        
        API-->>RQ: Deletion confirmed (550ms)
        Note over RQ: {success: true,<br/>expenses_deleted: 25,<br/>members_affected: 6}
        
        RQ->>RQ: Remove group from cache
        RQ->>API: Refresh group list
        API->>FS: Get remaining groups
        FS-->>API: Groups (caches cleared)
        API-->>RQ: Return groups
        
        RQ-->>OWNER: Show success<br/>"Group deleted successfully"<br/>Redirect to dashboard
    end
    
    Note over OWNER: Group removed from list<br/>All 6 members see change<br/>on next login (within 30s)
```

**Key Points:**
- Requires owner permission (not admin)
- Must settle all balances first (or force flag)
- Cascade deletes 100+ documents
- 25+ cache keys invalidated for all members
- Audit log for compliance
- Permanent deletion (cannot undo)

---

## 12. Cache Invalidation Flow

### Complete Pattern Across System

```mermaid
flowchart TD
    START([Write Operation Occurs]) --> IDENTIFY[Identify Operation Type]
    
    IDENTIFY --> TYPE{What Changed?}
    
    TYPE -->|User Profile Update| USER_INV[Invalidate User Caches]
    TYPE -->|Group Data Update| GROUP_INV[Invalidate Group Caches]
    TYPE -->|Expense Created| EXPENSE_INV[Invalidate Expense Caches]
    TYPE -->|Settlement Created| SETTLE_INV[Invalidate Settlement Caches]
    TYPE -->|Invitation Accepted| INVITE_INV[Invalidate Invitation Caches]
    TYPE -->|Member Added/Removed| MEMBER_INV[Invalidate Member Caches]
    
    USER_INV --> U_KEYS[Delete Keys:<br/>• user_profile:UID<br/>• display_name:UID<br/>• user_groups:UID<br/>• user_groups:UID_summary]
    
    GROUP_INV --> G_KEYS[Delete Keys:<br/>• group_full:GID<br/>• group_balance_formatted:GID<br/>• expenses:group:GID*<br/>• For EACH member:<br/>  - user_groups:MEMBER*]
    
    EXPENSE_INV --> E_KEYS[Delete Keys:<br/>• group_full:GID<br/>• group_balance_formatted:GID<br/>• expenses:group:GID*<br/>• For EACH split participant:<br/>  - user_groups:MEMBER*]
    
    SETTLE_INV --> S_KEYS[Delete Keys:<br/>• group_balance_formatted:GID<br/>• settlements:group:GID*<br/>• For from & to users:<br/>  - user_groups:UID*]
    
    INVITE_INV --> I_KEYS[Delete Keys:<br/>• invitations:enriched:UID*<br/>  (wildcard for pagination)<br/>• user_groups:UID*<br/>• group_full:GID<br/>• For EACH existing member:<br/>  - user_groups:MEMBER*]
    
    MEMBER_INV --> M_KEYS[Delete Keys:<br/>• group_full:GID<br/>• group_balance_formatted:GID<br/>• For ALL members:<br/>  - user_groups:MEMBER*]
    
    U_KEYS --> EXECUTE[Execute Deletions in Redis]
    G_KEYS --> EXECUTE
    E_KEYS --> EXECUTE
    S_KEYS --> EXECUTE
    I_KEYS --> EXECUTE
    M_KEYS --> EXECUTE
    
    EXECUTE --> LOG[Log Cache Invalidation]
    LOG --> METRICS[Update Cache Metrics]
    METRICS --> DONE([Cache Invalidated])
    
    style START fill:#90EE90
    style DONE fill:#90EE90
    style EXECUTE fill:#FF6B6B
```

**Invalidation Patterns:**

**Pattern 1: Single User**
```python
keys = [
    f"user_profile:{user_id}",
    f"display_name:{user_id}",
    f"user_groups:{user_id}",
    f"user_groups:{user_id}_summary"
]
redis.delete(*keys)
```

**Pattern 2: Group Members (Loop)**
```python
for member_id in member_ids:
    redis.delete(
        f"user_groups:{member_id}",
        f"user_groups:{member_id}_summary"
    )
```

**Pattern 3: Wildcard (Pagination)**
```python
pattern = f"invitations:enriched:{user_id}*"
keys = redis.keys(pattern)  # Get all matching
if keys:
    redis.delete(*keys)  # Delete all at once
```

**Pattern 4: Group Data**
```python
redis.delete(
    f"group_full:{group_id}",
    f"group_balance_formatted:{group_id}"
)
# Plus wildcard for expenses
pattern = f"expenses:group:{group_id}*"
keys = redis.keys(pattern)
if keys:
    redis.delete(*keys)
```

---

**End of Individual Mermaid Flows**

All flowcharts are ready for professional documentation and can be rendered in any Mermaid-compatible viewer or exported as images.
