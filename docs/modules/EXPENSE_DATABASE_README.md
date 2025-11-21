# Expense Database Storage

## Overview
This folder is used to organize and reference expense-related data storage in Firebase/Firestore and Redis cache.

## Data Storage

### Firebase/Firestore Collections
All expense data is stored in the following Firestore collections:

1. **users** - User profiles and preferences
   - Document ID: User UID from Firebase Auth
   - Fields: email, username, display_name, profile_picture, created_at, updated_at

2. **groups** - Expense groups (trips, roommates, etc.)
   - Document ID: Auto-generated
   - Fields: name, description, currency, created_by, created_at, member_count

3. **group_members** - Group membership tracking
   - Document ID: Auto-generated
   - Fields: group_id, user_id, role, joined_at, is_active

4. **group_invitations** - Pending group invitations
   - Document ID: Auto-generated
   - Fields: group_id, email, invited_by, status, created_at, expires_at

5. **expenses** - Individual expense records
   - Document ID: Auto-generated
   - Fields: group_id, amount, currency, description, category, paid_by, created_at, splits[]

6. **settlements** - Payment settlements between users
   - Document ID: Auto-generated
   - Fields: group_id, from_user, to_user, amount, currency, status, created_at, settled_at

7. **balances** - Real-time balance tracking
   - Document ID: {user_id}_{group_id}
   - Fields: user_id, group_id, balance, currency, last_updated

### Redis Cache Storage
Cached data is stored in Redis with the following key patterns:

- `expense:user:{uid}` - User data (TTL: 1 hour)
- `expense:group:{group_id}` - Group data (TTL: 30 minutes)
- `expense:expense:{expense_id}` - Expense data (TTL: 15 minutes)
- `expense:balance:{user_id}:{group_id}` - Balance data (TTL: 5 minutes)
- `expense:user_groups:{uid}` - User's groups list (TTL: 30 minutes)
- `expense:group_expenses:{group_id}` - Group's expenses list (TTL: 15 minutes)
- `expense:user_expenses:{uid}` - User's expenses list (TTL: 15 minutes)
- `expense:invitations:{email}` - Pending invitations (TTL: 10 minutes)
- `expense:settlements:{group_id}` - Group settlements (TTL: 15 minutes)

## Multi-Currency Support

All monetary data is stored with a currency field supporting:
- **USD** - US Dollar ($)
- **EUR** - Euro (€)
- **INR** - Indian Rupee (₹)
- **GBP** - British Pound (£)
- **JPY** - Japanese Yen (¥)
- **CAD** - Canadian Dollar (C$)
- **AUD** - Australian Dollar (A$)
- **CHF** - Swiss Franc (CHF)
- **CNY** - Chinese Yuan (¥)
- And more...

## Data Organization

### User Account Creation Flow
When a user creates an account:
1. Firebase Auth creates the user authentication
2. User profile is created in `users` collection
3. User data is cached in Redis with key `expense:user:{uid}`
4. All data is automatically stored in this database structure

### Expense Creation Flow
When an expense is created:
1. Expense record is created in `expenses` collection
2. Expense splits are stored within the expense document
3. Balances are updated in `balances` collection
4. All data is cached in Redis for fast access
5. Cache is invalidated when data changes

### Data Persistence
- **Firebase/Firestore**: Permanent storage, survives server restarts
- **Redis Cache**: Temporary storage, rebuilt from Firestore as needed
- **Backup**: Firestore has automatic backups and point-in-time recovery

## Code Location
All code that interacts with this database is located in:
- `web/backend/expense_engine/` - Complete expense management system

The code includes:
- `firebase_operations.py` - Firestore database operations
- `cache_operations.py` - Redis cache operations
- `models.py` - Data models and schemas
- `service.py` - Business logic combining Firebase and Redis
- `routes.py` - REST API endpoints

## Configuration

### Firebase Configuration
Set in environment variables:
```bash
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
```

### Redis Configuration
Set in environment variables:
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
```

## Data Access
Data is accessed through the ExpenseService which:
1. Checks Redis cache first (fast)
2. Falls back to Firestore if not cached
3. Updates cache after Firestore reads
4. Invalidates cache after writes

## Notes
- This folder is for organizational reference
- Actual data is stored in Firebase Cloud Firestore and Redis
- No local files are stored here
- All data operations are handled by code in `expense_engine/`
