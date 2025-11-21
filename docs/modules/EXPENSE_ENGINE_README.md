# Expense Management System Backend

Production-ready expense tracking system similar to Splitwise.

## Structure

```
expense_database/
├── __init__.py                 # Module initialization
├── models.py                   # Data models (User, Group, Expense, etc.)
├── firebase_service.py         # Firebase/Firestore operations
├── cache_service.py            # Redis caching layer
├── service.py                  # Main service (combines Firebase + Redis)
├── email_service.py            # Email notifications
└── routes.py                   # Flask API endpoints
```

## Key Components

### Models (`models.py`)
- **User**: User profiles with unique usernames
- **Group**: Expense groups with members
- **Expense**: Individual or group expenses
- **ExpenseSplit**: How expenses are divided
- **Settlement**: Payment records
- **Balance**: Calculated balances

### Firebase Service (`firebase_service.py`)
- Direct database operations
- CRUD for all models
- Balance calculations
- Group membership management

### Cache Service (`cache_service.py`)
- Redis-based caching
- Automatic cache invalidation
- Performance optimization
- Handles 100+ concurrent users

### Main Service (`service.py`)
- Combines Firebase + Redis
- Cache-aside pattern
- Business logic layer
- Single point of access

### Email Service (`email_service.py`)
- Group invitations
- Expense notifications
- Settlement confirmations
- HTML email templates

### Routes (`routes.py`)
- RESTful API endpoints
- Authentication middleware
- Input validation
- Error handling

## Usage

```python
from database.expense_database.service import expense_service

# Create user
user = expense_service.create_user(
    uid="firebase_uid",
    email="user@example.com",
    username="johndoe"
)

# Create group
group = expense_service.create_group(
    name="Roommates",
    created_by="firebase_uid"
)

# Add expense
expense = expense_service.create_expense(
    description="Dinner",
    amount=100.0,
    paid_by="firebase_uid",
    category="food",
    splits=[
        {"user_id": "user1", "amount": 50},
        {"user_id": "user2", "amount": 50}
    ],
    group_id=group['group_id']
)

# Get balance
balance = expense_service.get_user_balance("firebase_uid", group['group_id'])
```

## Configuration

Required environment variables:
- `REDIS_URL`: Redis connection string
- `REDIS_MAX_CONNECTIONS`: Connection pool size (default: 50)
- `SMTP_USER`: Email account
- `SMTP_PASSWORD`: Email password
- `FRONTEND_URL`: Frontend URL for email links

## Performance

- **Caching**: Intelligent Redis caching with automatic invalidation
- **Scalability**: Handles 100+ concurrent users
- **Optimization**: Database query optimization with Firestore indexes
- **Monitoring**: Cache statistics and health checks available

## API Endpoints

All endpoints prefixed with `/api/expense`:

- User: `/user/profile`, `/user/search`
- Groups: `/groups`, `/groups/<id>`, `/groups/<id>/members`
- Invitations: `/invitations`, `/invitations/<id>/accept`
- Expenses: `/expenses`, `/expenses/<id>`, `/expenses/personal`
- Settlements: `/settlements`, `/settlements/group/<id>`
- Balances: `/balance`, `/balance/breakdown`, `/balance/group/<id>`
- Utilities: `/health`, `/cache/stats`, `/categories`

See [Complete Documentation](../../docs/EXPENSE_MANAGEMENT_COMPLETE_GUIDE.md) for details.

## Testing

```bash
# Health check
curl http://localhost:5000/api/expense/health

# With authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/expense/user/profile
```

## Production Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with more workers
gunicorn -w 8 -b 0.0.0.0:5000 --timeout 120 app:app
```

## Monitoring

```python
# Get system health
GET /api/expense/health

# Get cache statistics
GET /api/expense/cache/stats
```

## Security

- Firebase JWT authentication
- Role-based access control
- Input validation
- SQL injection prevention (NoSQL)
- XSS protection
- CORS configuration

## Error Handling

All operations return structured responses:

```json
{
  "success": true,
  "data": {...}
}

// Or on error:
{
  "error": "Description",
  "detail": "Additional info"
}
```

---

Built for production. Ready to scale. 🚀
