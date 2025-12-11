# Expense Engine Quick Reference Guide

## Overview

This guide provides quick access to key implementation patterns for the expense engine migration.

---

## 1. Project Structure Comparison

### Current (expense_engine_2)
```
expense_engine_2/
├── service.py                 # 2744 lines (monolithic)
├── firebase_operations.py     # 1672 lines
├── balance_manager.py         # 1214 lines
└── routes/                    # Direct Firebase calls
```

### Target (expense_engine)
```
expense_engine/
├── models/                    # Pydantic models (~50-100 lines each)
├── repositories/              # Data access (~100-200 lines each)
├── services/                  # Business logic (~200-300 lines each)
├── routes/                    # Thin controllers (~100-150 lines each)
└── middleware/                # Cross-cutting concerns
```

---

## 2. Firebase Collections

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `expense_groups` | Group documents | name, currency, created_by |
| `expense_group_members` | Memberships | user_id, group_id, role, is_active |
| `expense_group_balances` | Denormalized balances | balances[], debts[], version |
| `expense_expenses` | Expenses | amount, paid_by, splits[], is_deleted |
| `expense_settlements` | Payments | payer_id, payee_id, amount |
| `expense_invitations` | Invitations | invitee_email, status, expires_at |

---

## 3. Required Firestore Indexes

Deploy these indexes before going live:

```json
{
  "indexes": [
    {
      "collectionGroup": "expense_expenses",
      "fields": [
        { "fieldPath": "group_id", "order": "ASCENDING" },
        { "fieldPath": "is_deleted", "order": "ASCENDING" },
        { "fieldPath": "expense_date", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "expense_group_members",
      "fields": [
        { "fieldPath": "user_id", "order": "ASCENDING" },
        { "fieldPath": "is_active", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "expense_invitations",
      "fields": [
        { "fieldPath": "invited_user", "order": "ASCENDING" },
        { "fieldPath": "status", "order": "ASCENDING" },
        { "fieldPath": "created_at", "order": "DESCENDING" }
      ]
    }
  ]
}
```

```bash
firebase deploy --only firestore:indexes
```

---

## 4. Security Configuration

### Rate Limits

```python
# Per-user limits
RATE_LIMITS = {
    'read_light': '100/minute',
    'read_heavy': '30/minute',
    'create': '20/minute',
    'update': '30/minute',
    'delete': '10/minute',
    'settlement': '10/minute'
}
```

### RBAC Roles

| Role | Create Expense | Edit Own | Delete Own | Manage Group |
|------|----------------|----------|------------|--------------|
| Admin | ✓ | ✓ | ✓ | ✓ |
| Owner | ✓ | ✓ | ✓ | ✓ |
| Member | ✓ | ✓ | ✓ | ✗ |
| Viewer | ✗ | ✗ | ✗ | ✗ |

---

## 5. Cache Configuration

```python
# Redis TTL values (seconds)
CACHE_TTL = {
    'user': 3600,           # 1 hour
    'group': 1800,          # 30 minutes
    'group_full': 1200,     # 20 minutes
    'balance': 1800,        # 30 minutes
    'expense': 900,         # 15 minutes
    'invitation': 600,      # 10 minutes
    'display_name': 3600,   # 1 hour
    'idempotency': 86400    # 24 hours
}
```

---

## 6. API Performance Targets

| Endpoint | P50 | P95 | Firestore Reads |
|----------|-----|-----|-----------------|
| GET /groups/{id}/full | <200ms | <500ms | 10-15 |
| POST /expenses | <150ms | <300ms | 3-5 |
| GET /groups | <100ms | <250ms | 5-10 |
| GET /balances | <50ms | <150ms | 1-2 |
| POST /settlements | <200ms | <400ms | 4-6 |

---

## 7. Frontend Integration Patterns

### React Query Setup

```javascript
// queryClient.js
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,        // 30 seconds
      gcTime: 5 * 60 * 1000,       // 5 minutes
      refetchOnWindowFocus: true,
    }
  }
});
```

### Firestore Listener Pattern

```javascript
// Listen to expenses in real-time
useEffect(() => {
  if (!groupId) return;
  
  const unsubscribe = expenseFirestoreListener.listenToGroupExpenses(
    groupId,
    (expenses) => {
      queryClient.setQueryData(['group', groupId], (old) => ({
        ...old,
        expenses
      }));
    }
  );
  
  return () => unsubscribe();
}, [groupId]);
```

### Optimistic Update Pattern

```javascript
// Create expense with instant UI feedback
const createExpenseMutation = useMutation({
  mutationFn: (data) => expenseApi.createExpense(data),
  onMutate: async (newExpense) => {
    await queryClient.cancelQueries(['group', newExpense.group_id]);
    const previous = queryClient.getQueryData(['group', newExpense.group_id]);
    
    // Optimistically add expense
    queryClient.setQueryData(['group', newExpense.group_id], (old) => ({
      ...old,
      expenses: [{ ...newExpense, is_optimistic: true }, ...old.expenses]
    }));
    
    return { previous };
  },
  onError: (err, newExpense, context) => {
    // Rollback on error
    queryClient.setQueryData(['group', newExpense.group_id], context.previous);
  },
  onSettled: () => {
    // Refetch to sync with server
    queryClient.invalidateQueries(['group', newExpense.group_id]);
  }
});
```

---

## 8. Error Handling

### Backend Error Response Format

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Amount must be between $0.01 and $1,000,000",
  "code": "E010",
  "details": {
    "field": "amount",
    "value": -50,
    "constraint": "positive"
  }
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| E001-E003 | Validation errors |
| E004-E005 | Authentication errors |
| E006-E007 | Authorization errors |
| E008-E009 | Resource errors |
| E010 | Business rule violation |
| E011-E012 | Server errors |

---

## 9. Monitoring Checklist

### Daily Checks
- [ ] API error rate < 1%
- [ ] P95 latency < 500ms
- [ ] Cache hit rate > 70%
- [ ] No slow queries (> 1s)

### Weekly Checks
- [ ] Firestore read/write costs
- [ ] Redis memory usage
- [ ] Error log review
- [ ] Performance trend analysis

---

## 10. Rollback Commands

```bash
# Disable new features
export USE_NEW_EXPENSE_SERVICE=false
export USE_NEW_BALANCE_SERVICE=false

# Restart application
pm2 restart expense-api

# Or with Docker
docker-compose restart expense-api
```

---

## Quick Commands

```bash
# Deploy Firestore indexes
firebase deploy --only firestore:indexes

# Deploy Firestore rules
firebase deploy --only firestore:rules

# Run backend tests
pytest tests/ -v --cov=expense_engine

# Run frontend tests
npm test -- --coverage

# Check Redis
redis-cli ping
redis-cli info memory
redis-cli keys "expense:*" | head -20
```

---

*Quick Reference v1.0 | November 2025*
