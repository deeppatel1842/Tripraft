# Expense Engine - Professional Splitwise-Style System

## Overview

Production-ready expense splitting engine designed for scalability, security, and performance.

## Features

✅ **Zero Hardcoding** - All values from config/environment
✅ **Incremental Balance Calculations** - No expensive full scans
✅ **Smart Redis Caching** - 90%+ hit rate target
✅ **Row-Level Security** - Firestore security rules
✅ **RBAC Authorization** - Owner/Admin/Member roles
✅ **Rate Limiting** - Handles 1000+ concurrent users
✅ **Real-Time Updates** - Firestore listeners
✅ **Type-Safe Models** - Pydantic validation
✅ **Clean Architecture** - Repository → Service → Route layers

## Directory Structure

```
expense_engine/
├── __init__.py              # Package initialization
├── config.py                # Zero-hardcode configuration
├── constants.py             # Business constants & enums
├── exceptions.py            # Custom exceptions
├── README.md               # This file
│
├── models/                  # Pydantic data models
│   ├── user.py
│   ├── group.py
│   ├── expense.py
│   ├── settlement.py
│   ├── balance.py
│   └── invitation.py
│
├── repositories/            # Data access layer
│   ├── base.py             # Base repository
│   ├── user_repository.py
│   ├── group_repository.py
│   ├── expense_repository.py
│   ├── settlement_repository.py
│   ├── balance_repository.py
│   └── invitation_repository.py
│
├── services/                # Business logic
│   ├── group_service.py
│   ├── expense_service.py
│   ├── balance_service.py
│   ├── settlement_service.py
│   ├── invitation_service.py
│   └── cache_service.py
│
├── routes/                  # REST API endpoints
│   ├── group_routes.py
│   ├── expense_routes.py
│   ├── settlement_routes.py
│   ├── invitation_routes.py
│   └── user_routes.py
│
├── middleware/              # Cross-cutting concerns
│   ├── auth.py             # JWT authentication
│   ├── rbac.py             # Role-based access control
│   ├── rate_limiter.py     # Rate limiting
│   ├── request_validator.py
│   └── error_handler.py
│
├── utils/                   # Utilities
│   ├── validators.py
│   ├── formatters.py
│   ├── decimal_utils.py
│   └── transaction_helper.py
│
├── workers/                 # Background jobs
│   ├── cleanup_worker.py
│   └── analytics_worker.py
│
└── monitoring/              # Observability
    ├── metrics.py
    ├── logger.py
    └── health_check.py
```

## Configuration

All configuration via environment variables (see `config.py`):

### Required
- `FIREBASE_PROJECT_ID` - Firebase project
- `REDIS_HOST` - Redis server host
- `REDIS_PORT` - Redis server port

### Optional
- `REDIS_MAX_CONNECTIONS` - Default: 50
- `RATE_LIMIT_READS` - Default: 60/min
- `RATE_LIMIT_WRITES` - Default: 30/min
- `MAX_GROUP_MEMBERS` - Default: 50
- `MAX_EXPENSE_AMOUNT` - Default: 1000000
- `LOG_LEVEL` - Default: INFO

## Firestore Collections

**No conflicts with Group Planner!**

- `expense_groups` - Expense groups
- `expense_group_members` - Group memberships
- `expense_invitations` - Group invitations
- `expense_expenses` - Individual expenses
- `expense_settlements` - Payments/settlements
- `expense_group_balances` - Balance calculations
- `expense_group_summaries` - User's group summaries

## API Endpoints

### Groups
- `GET /api/expense/groups` - List user's groups
- `GET /api/expense/groups/:gid/summary` - Group summary
- `POST /api/expense/groups` - Create group
- `PATCH /api/expense/groups/:gid` - Update group
- `DELETE /api/expense/groups/:gid` - Delete group

### Expenses
- `GET /api/expense/groups/:gid/expenses` - List expenses (paginated)
- `POST /api/expense/groups/:gid/expenses` - Create expense
- `PATCH /api/expense/groups/:gid/expenses/:eid` - Update expense
- `DELETE /api/expense/groups/:gid/expenses/:eid` - Delete expense

### Settlements
- `GET /api/expense/groups/:gid/settlements` - List settlements
- `POST /api/expense/groups/:gid/settlements` - Create settlement

### Invitations
- `GET /api/expense/invitations` - List user's invitations
- `POST /api/expense/groups/:gid/invite` - Send invitation
- `POST /api/expense/invitations/:iid/accept` - Accept invitation
- `POST /api/expense/invitations/:iid/decline` - Decline invitation

## Security

### Authentication
- Firebase JWT token required for all endpoints
- Token validation via `@require_auth` decorator

### Authorization (RBAC)
- **Owner**: Full control (delete group, manage members, all expenses)
- **Admin**: Manage expenses, invite members
- **Member**: Create/edit own expenses, create settlements

### Firestore Security Rules
- Row-level security
- Users can only access groups they're members of
- Expenses/settlements/balances protected by group membership

## Performance

### Targets
- Cache hit rate: >90%
- API latency (p95): <200ms
- Balance read: <50ms
- Supports: 1000+ concurrent users

### Caching Strategy
- User groups: 60s TTL
- Group summary: 30s TTL
- Group expenses: 60s TTL
- Targeted invalidation on writes

### Balance Calculation
- **Incremental updates** (no full scans)
- Firestore transactions for atomicity
- O(1) read complexity

## Development

### Install Dependencies
```bash
pip install pydantic redis firebase-admin flask
```

### Run Tests
```bash
pytest expense_engine/tests/
```

### Start Server
```bash
python app.py
```

## Migration from expense_engine_2

See `EXPENSE_ENGINE_MIGRATION_PLAN.md` for full migration guide.

### Feature Flag
```python
USE_NEW_ENGINE = os.getenv('USE_NEW_ENGINE', 'false').lower() == 'true'

if USE_NEW_ENGINE:
    app.register_blueprint(expense_engine_routes)
else:
    app.register_blueprint(expense_engine_2_routes)
```

## Monitoring

### Metrics
- Firestore read/write counts
- Redis hit/miss ratio
- API endpoint latencies
- Active user count

### Logging
- Structured JSON logs
- Performance logging (enabled via `ENABLE_PERF_LOGGING`)
- Audit trail in `expense_activities`

## Architecture Principles

1. **Zero Hardcoding** - All config externalized
2. **Separation of Concerns** - Repository → Service → Route
3. **Type Safety** - Pydantic models with validation
4. **Security First** - Auth on every endpoint
5. **Performance** - Caching + incremental calculations
6. **Scalability** - Rate limiting + connection pooling
7. **Observability** - Metrics + structured logging

## License

© TripRaft Team 2025
