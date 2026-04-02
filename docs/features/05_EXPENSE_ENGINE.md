# Feature: Expense Management Engine

## Overview

TripRaft includes a full expense tracking and settlement engine. Users create expense groups, add members, log expenses with configurable split types, and settle debts. The engine maintains real-time balance tracking with Decimal precision and supports a simplified debt algorithm to minimize the number of settlement transactions.

---

## System Flow

```
                    EXPENSE LIFECYCLE
                    ==================

User A (Admin)                Flask Backend                   Database
     │                              │                            │
     │  POST /expense-groups        │                            │
     │  {name: "Barcelona Trip",    │                            │
     │   currency: "EUR",           │                            │
     │   description: "..."}        │                            │
     │─────────────────────────────>│                            │
     │                              │  GroupServiceSQL.create()  │
     │                              │  INSERT Group              │
     │                              │  INSERT GroupMember(admin) │
     │                              │──────────────────────────>│
     │  201 Created {group}         │                            │
     │<─────────────────────────────│                            │
     │                              │                            │
     │  POST /expense-invitations   │                            │
     │  {group_id, email: "B@..."}  │                            │
     │─────────────────────────────>│                            │
     │                              │  INSERT Invitation         │
     │                              │  (7-day expiry)            │
     │                              │──────────────────────────>│
     │                              │  send_invitation_email     │
     │                              │  .delay() → Celery         │
     │  201 Created {invitation}    │                            │
     │<─────────────────────────────│                            │


                    EXPENSE CREATION + SPLIT
                    =========================

User A                       Flask Backend                    Database
     │                              │                            │
     │  POST /expenses              │                            │
     │  {group_id: "...",           │                            │
     │   amount: 120.00,            │                            │
     │   description: "Dinner",     │                            │
     │   category: "food",          │                            │
     │   paid_by: "A_user_id",      │                            │
     │   split_type: "equal",       │                            │
     │   split_with: ["A","B","C"]} │                            │
     │─────────────────────────────>│                            │
     │                              │                            │
     │                              │  ExpenseServiceSQL.create()│
     │                              │  1. Validate group member  │
     │                              │  2. Calculate splits:      │
     │                              │     equal → 40.00 each     │
     │                              │                            │
     │                              │  INSERT Expense            │
     │                              │  INSERT ExpenseSplit (x3)  │
     │                              │  ┌─────────────────────┐  │
     │                              │  │ A: owes 40.00       │  │
     │                              │  │ B: owes 40.00       │  │
     │                              │  │ C: owes 40.00       │  │
     │                              │  │ A paid: -120.00     │  │
     │                              │  │ Net: A is owed 80   │  │
     │                              │  │       B owes 40     │  │
     │                              │  │       C owes 40     │  │
     │                              │  └─────────────────────┘  │
     │                              │                            │
     │                              │  UPDATE GroupBalance       │
     │                              │  (recalculate per-user)    │
     │                              │──────────────────────────>│
     │                              │                            │
     │                              │  INSERT ExpenseHistory     │
     │                              │  (action: "created")       │
     │                              │──────────────────────────>│
     │                              │                            │
     │  201 Created {expense}       │                            │
     │<─────────────────────────────│                            │


                    SETTLEMENT FLOW
                    ================

User B                       Flask Backend                    Database
     │                              │                            │
     │  GET /expense-groups/        │                            │
     │  {group_id}/simplified-debts │                            │
     │─────────────────────────────>│                            │
     │                              │  SettlementServiceSQL      │
     │                              │  .simplify_debts()         │
     │                              │                            │
     │                              │  Algorithm:                │
     │                              │  1. Net balance per user   │
     │                              │  2. Sort creditors (desc)  │
     │                              │  3. Sort debtors (desc)    │
     │                              │  4. Match largest debtor   │
     │                              │     to largest creditor    │
     │                              │  5. Minimum transactions   │
     │                              │──────────────────────────>│
     │                              │                            │
     │  200 OK                      │                            │
     │  {debts: [                   │                            │
     │    {from: "B", to: "A",      │                            │
     │     amount: 40.00},          │                            │
     │    {from: "C", to: "A",      │                            │
     │     amount: 40.00}           │                            │
     │  ]}                          │                            │
     │<─────────────────────────────│                            │
     │                              │                            │
     │  POST /settlements           │                            │
     │  {group_id, from: "B",       │                            │
     │   to: "A", amount: 40.00}    │                            │
     │─────────────────────────────>│                            │
     │                              │  INSERT Settlement         │
     │                              │  UPDATE GroupBalance       │
     │                              │  (B: 0, A: owed 40 now)   │
     │                              │──────────────────────────>│
     │  201 Created {settlement}    │                            │
     │<─────────────────────────────│                            │
```

---

## Split Types

| Type | Calculation | Example (120 EUR, 3 people) |
|------|------------|---------------------------|
| **Equal** | Total / N (equal shares) | A: 40, B: 40, C: 40 |
| **Exact** | User specifies exact amounts per person | A: 60, B: 40, C: 20 |
| **Percentage** | User specifies percentage per person | A: 50%, B: 30%, C: 20% → 60, 36, 24 |
| **Shares** | Ratio-based (e.g., 2:1:1) | A: 60, B: 30, C: 30 |

All amounts stored and computed using Python `Decimal` for currency precision.

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/api/v1/expense_groups.py` | Group CRUD, member management, join-by-code (11 endpoints) |
| `app/api/v1/expenses.py` | Expense CRUD, listing, history (9 endpoints) |
| `app/api/v1/settlements.py` | Settlement CRUD, balances, simplified debts (7 endpoints) |
| `app/api/v1/expense_invitations.py` | Invitation send/accept/decline/list (4 endpoints) |
| `app/services/expense_service.py` | ExpenseServiceSQL: create, update, delete, list, calculate_splits |
| `app/services/expense_group_service.py` | GroupServiceSQL: group lifecycle, member CRUD |
| `app/services/settlement_service.py` | SettlementServiceSQL: create, delete, balances, simplify_debts |
| `app/services/expense_invite_service.py` | InvitationServiceSQL: send, accept, decline, expire |
| `app/domain/expenses/models.py` | 8 models: Group, GroupMember, Expense, ExpenseSplit, Settlement, GroupBalance, Invitation, ExpenseHistory |
| `app/schemas/expenses.py` | CreateExpenseSchema, UpdateExpenseSchema |
| `app/schemas/expense_groups.py` | CreateExpenseGroupSchema, UpdateExpenseGroupSchema, JoinGroupSchema |
| `app/schemas/settlements.py` | CreateSettlementSchema |

### Frontend

| File | Purpose |
|------|---------|
| `src/components/expenses/jsx/ExpenseManager.jsx` | Main container: 30s smart polling, group/personal toggle |
| `src/components/expenses/jsx/TransactionList.jsx` | Paginated expense list with infinite scroll |
| `src/components/expenses/jsx/TransactionModal.jsx` | Create/edit expense modal with split type selection |
| `src/components/expenses/jsx/ExpenseSummary.jsx` | Summary cards: total spent, per-person breakdown |
| `src/components/expenses/jsx/GroupBalances.jsx` | Who owes whom visualization |
| `src/components/expenses/jsx/SettlementModal.jsx` | Record payment settlement |
| `src/components/expenses/jsx/SettlementHistoryModal.jsx` | Past settlements list |
| `src/components/expenses/jsx/ExpenseHistoryModal.jsx` | Expense edit audit trail |
| `src/components/expenses/jsx/GroupManager.jsx` | Group CRUD, member invitations |
| `src/components/expenses/jsx/PendingInvitations.jsx` | View and accept pending invitations |
| `src/components/expenses/jsx/MemberSpending.jsx` | Individual spending breakdown |
| `src/components/expenses/jsx/PersonalTabbedView.jsx` | Personal expense analytics |
| `src/components/expenses/jsx/TabbedGroupView.jsx` | Group expense analytics |
| `src/components/expenses/jsx/ExpenseAnalytics.jsx` | Charts and trend visualizations |
| `src/services/expenseApi.js` | All expense REST calls |
| `src/hooks/useExpenseQuery.js` | TanStack Query hooks for expenses, groups, settlements |
| `src/services/pdfExportService.js` | Client-side PDF report generation (jsPDF) |

---

## Database Models

```
groups (expense groups)
├── id (UUIDv7, PK)
├── name (String)
├── description (Text)
├── currency (String, default "USD")
├── created_by (FK → users.id)
├── invite_code (String, unique)
├── is_deleted (Boolean)
└── created_at, updated_at

group_members
├── id (UUIDv7, PK)
├── group_id (FK → groups.id)
├── user_id (FK → users.id)
├── role (String: admin, member)
└── joined_at

expenses
├── id (UUIDv7, PK)
├── group_id (FK → groups.id, nullable for personal)
├── amount (Decimal)
├── description (String)
├── category (String: food, transport, accommodation, etc.)
├── paid_by (FK → users.id)
├── split_type (String: equal, exact, percentage, shares)
├── date (DateTime)
├── is_deleted (Boolean, soft delete)
├── notes (Text)
└── created_at, updated_at

expense_splits
├── id (UUIDv7, PK)
├── expense_id (FK → expenses.id)
├── user_id (FK → users.id)
├── amount (Decimal)
├── percentage (Decimal, nullable)
├── shares (Integer, nullable)
└── created_at

settlements
├── id (UUIDv7, PK)
├── group_id (FK → groups.id)
├── payer_id (FK → users.id)
├── payee_id (FK → users.id)
├── amount (Decimal)
├── notes (Text)
└── created_at

group_balances
├── id (UUIDv7, PK)
├── group_id (FK → groups.id)
├── user_id (FK → users.id)
├── balance (Decimal)
└── updated_at

invitations (expense)
├── id (UUIDv7, PK)
├── group_id (FK → groups.id)
├── invited_by (FK → users.id)
├── email (String)
├── status (String: pending, accepted, declined, expired)
├── expires_at (DateTime, +7 days)
└── created_at

expense_history (audit trail)
├── id (UUIDv7, PK)
├── expense_id (FK → expenses.id)
├── action (String: created, updated, deleted)
├── changed_by (FK → users.id)
├── old_values (JSON)
├── new_values (JSON)
└── created_at
```

---

## Simplified Debt Algorithm

```
Input: Expenses and settlements for a group

Step 1: Calculate net balance per user
  For each user:
    balance = (total paid by user) - (total owed by user) + (settlements received) - (settlements paid)

Step 2: Split into creditors (balance > 0) and debtors (balance < 0)

Step 3: Sort creditors descending by amount, debtors descending by absolute amount

Step 4: Greedy matching
  While debtors and creditors exist:
    Take largest debtor (D) and largest creditor (C)
    Transfer = min(|D.balance|, C.balance)
    Record: D pays C the transfer amount
    Update both balances
    Remove any user with 0 balance

Result: Minimum number of transactions to settle all debts
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/expense-groups` | Required | Create group |
| GET | `/expense-groups` | Required | List user's groups |
| GET | `/expense-groups/{id}` | Required | Get group detail |
| GET | `/expense-groups/{id}/full` | Required | Full group with expenses + members |
| PUT | `/expense-groups/{id}` | Required | Update group |
| DELETE | `/expense-groups/{id}` | Required | Soft delete group |
| GET | `/expense-groups/{id}/members` | Required | List members |
| POST | `/expense-groups/{id}/members` | Required | Add member |
| DELETE | `/expense-groups/{id}/members/{mid}` | Required | Remove member |
| POST | `/expense-groups/{id}/leave` | Required | Leave group |
| POST | `/expense-groups/join` | Required | Join by code |
| POST | `/expenses` | Required | Create expense |
| GET | `/expenses` | Required | List expenses |
| GET | `/expenses/{id}` | Required | Get expense detail |
| PUT | `/expenses/{id}` | Required | Update expense |
| DELETE | `/expenses/{id}` | Required | Soft delete expense |
| GET | `/expense-groups/{id}/expenses` | Required | Group expenses |
| GET | `/me/expenses` | Required | Personal expenses |
| GET | `/expenses/{id}/history` | Required | Expense audit trail |
| POST | `/settlements` | Required | Record settlement |
| GET | `/settlements/{id}` | Required | Get settlement |
| DELETE | `/settlements/{id}` | Required | Delete settlement |
| GET | `/expense-groups/{id}/settlements` | Required | Group settlements |
| GET | `/expense-groups/{id}/balances` | Required | Per-user balances |
| GET | `/expense-groups/{id}/simplified-debts` | Required | Minimum transactions |
| GET | `/me/balance` | Required | User's total balance |
| POST | `/expense-invitations` | Required | Send invitation |
| GET | `/expense-invitations` | Required | List invitations |
| POST | `/expense-invitations/{id}/accept` | Required | Accept invitation |
| POST | `/expense-invitations/{id}/decline` | Required | Decline invitation |
