# 👥 Group Planner - Collaborative Trip Planning Module

> **Real-time trip coordination with polls, itineraries, and expense integration**

A comprehensive group trip planning system with member management, democratic voting, itinerary building, and seamless integration with the Expense Engine.

[![Production Ready](https://img.shields.io/badge/status-production-success)]()
[![Real-time Sync](https://img.shields.io/badge/sync-real--time-blue)]()
[![Integrated](https://img.shields.io/badge/expense-integrated-orange)]()

---

## 🎯 What is the Group Planner?

A complete trip coordination system for:
- **Group Management** - Create trip groups, invite members
- **Democratic Planning** - Polls & voting for destinations
- **Itinerary Building** - Day-by-day trip planning
- **Member Coordination** - Role-based permissions
- **Expense Integration** - Linked to Expense Engine
- **Email Notifications** - Activity updates

---

## 📁 Module Structure

```
Group_planner/
├── models.py              # Data models (Group, Member, Poll, etc.)
├── routes/                # API endpoints
│   ├── group_routes.py    # Group CRUD operations
│   ├── member_routes.py   # Member management
│   ├── poll_routes.py     # Polls & voting
│   └── itinerary_routes.py # Itinerary management
├── services/              # Business logic
│   ├── group_service.py   # Group operations
│   ├── member_service.py  # Member operations
│   └── poll_service.py    # Poll operations
└── README.md              # This file
```

---

## ✨ Key Features

### Group Management
- **Create Groups** - Trip planning groups with descriptions
- **Invite Members** - Email invitations with 7-day expiry
- **Role-Based Access** - Owner, admin, member permissions
- **Member Management** - Add, remove, update roles
- **Group Settings** - Customize preferences

### Democratic Planning
- **Create Polls** - Vote on destinations, dates, activities
- **Multiple Choice** - Single or multiple selection polls
- **Real-time Results** - Live vote tallies
- **Poll Expiry** - Time-limited voting
- **Weighted Voting** - Optional vote weighting by role

### Itinerary Builder
- **Day-by-Day Planning** - Organize trip schedule
- **Activity Management** - Add, edit, reorder activities
- **Time Slots** - Schedule with start/end times
- **Location Integration** - Link to Google Places
- **Collaborative Editing** - All members can contribute

### Expense Integration
- **Linked Groups** - Auto-connect to Expense Engine groups
- **Shared Balances** - View expenses within trip context
- **Budget Tracking** - Monitor trip spending
- **Settlement View** - See who owes what

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Firebase Project (Firestore + Auth)
- Redis 6.0+ (for caching)

### Installation

```bash
# Navigate to backend
cd web/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment (.env file)
FIREBASE_PROJECT_ID=your-project
GP_CACHE_TTL_GROUPS=600
GP_MAX_MEMBERS=50

# Run application
python run.py
```

**Test the API:**
```bash
curl http://localhost:5000/api/group/health
```

---

## 🔌 API Endpoints

### Group Management
```
POST   /api/group/groups              # Create group
GET    /api/group/groups              # List user's groups
GET    /api/group/groups/<id>         # Get group details
PUT    /api/group/groups/<id>         # Update group
DELETE /api/group/groups/<id>         # Delete group
```

### Member Management
```
POST   /api/group/groups/<id>/members      # Add member
GET    /api/group/groups/<id>/members      # List members
PUT    /api/group/groups/<id>/members/<uid> # Update member role
DELETE /api/group/groups/<id>/members/<uid> # Remove member
POST   /api/group/groups/<id>/invite       # Send invitation
```

### Polls & Voting
```
POST   /api/group/groups/<id>/polls        # Create poll
GET    /api/group/groups/<id>/polls        # List polls
GET    /api/group/groups/<id>/polls/<poll_id>  # Get poll
POST   /api/group/groups/<id>/polls/<poll_id>/vote  # Cast vote
DELETE /api/group/groups/<id>/polls/<poll_id>  # Delete poll
```

### Itinerary
```
POST   /api/group/groups/<id>/itinerary    # Add activity
GET    /api/group/groups/<id>/itinerary    # Get full itinerary
PUT    /api/group/groups/<id>/itinerary/<day>  # Update day
DELETE /api/group/groups/<id>/itinerary/<day>/<activity_id>  # Remove activity
```

---

## 🏗️ Architecture

### Data Models

#### Group
```python
{
  "group_id": "uuid",
  "name": "Europe Trip 2025",
  "description": "2-week adventure",
  "created_by": "user_id",
  "created_at": "timestamp",
  "members": [...],  # Subcollection
  "settings": {
    "max_members": 50,
    "expense_group_id": "linked_expense_group"
  }
}
```

#### Member
```python
{
  "uid": "user_id",
  "role": "owner|admin|member|viewer",
  "joined_at": "timestamp",
  "display_name": "John Doe",
  "email": "john@example.com"
}
```

#### Poll
```python
{
  "poll_id": "uuid",
  "group_id": "group_id",
  "question": "Which city should we visit?",
  "options": ["Paris", "London", "Rome"],
  "votes": {"user_id": "Paris"},
  "created_by": "user_id",
  "expires_at": "timestamp",
  "multiple_choice": false
}
```

#### Itinerary Activity
```python
{
  "activity_id": "uuid",
  "day": 1,
  "title": "Visit Eiffel Tower",
  "description": "Morning visit",
  "start_time": "09:00",
  "end_time": "12:00",
  "location": {
    "place_id": "google_place_id",
    "name": "Eiffel Tower",
    "coordinates": [lat, lng]
  },
  "created_by": "user_id"
}
```

---

## 🔒 Security

### Authentication
- **Firebase JWT** verification on all endpoints
- **User context** extracted from token claims

### Authorization (RBAC)
- **Owner** - Full control (delete group, manage members)
- **Admin** - Management (add members, create polls)
- **Member** - Participate (vote, suggest activities)
- **Viewer** - Read-only access

### Protection
- **Rate limiting** - 60 req/min per user
- **Input validation** - All data sanitized
- **Audit logging** - Critical operations logged

---

## 📊 Configuration

Environment variables for Group Planner:

```bash
# Cache Settings (seconds)
GP_CACHE_TTL_GROUPS=300
GP_CACHE_TTL_MEMBERS=600
GP_CACHE_TTL_POLLS=600
GP_CACHE_TTL_INVITATIONS=300
GP_CACHE_TTL_ITINERARY=600

# Business Rules
GP_MAX_MEMBERS=50
GP_MAX_PLACES=100
GP_MAX_POLLS=50
GP_MAX_CHECKLIST_ITEMS=100

# Email Configuration
GP_EMAIL_ENABLED=True
GP_EMAIL_TIMEOUT=5.0

# Invitation Settings
GP_INVITATION_EXPIRY_DAYS=7
GP_MAX_PENDING_INVITATIONS=10

# Feature Flags
GP_ENABLE_EXPENSE_INTEGRATION=True
GP_ENABLE_REAL_TIME_UPDATES=False
```

---

## 🌐 Expense Integration

### How It Works

1. **Create Group Planner Group**
   ```bash
   POST /api/group/groups
   {
     "name": "Europe Trip 2025",
     "enable_expenses": true
   }
   ```

2. **Auto-Create Expense Group**
   - System automatically creates linked Expense Engine group
   - Same members, same permissions
   - Bidirectional synchronization

3. **Use Both Systems**
   - **Group Planner**: Plan activities, vote on destinations
   - **Expense Engine**: Track spending, split bills
   - **Unified View**: See both in trip dashboard

### Sync Behavior
- **Add Member**: Added to both groups
- **Remove Member**: Removed from both groups
- **Update Role**: Synced across both systems
- **Delete Group**: Option to keep or delete expense group

---

## 📈 Performance

### Caching Strategy
- **Groups**: 5-10 minute TTL
- **Members**: 10 minute TTL
- **Polls**: 10 minute TTL (live results)
- **Itinerary**: 10 minute TTL

### Optimization
- **Redis caching** for frequently accessed data
- **Firestore indexes** for fast queries
- **Batch operations** for bulk updates
- **Connection pooling** for database

---

## 🧪 Testing

### Manual Testing
```bash
# Create group
curl -X POST http://localhost:5000/api/group/groups \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Trip","description":"Test"}'

# Create poll
curl -X POST http://localhost:5000/api/group/groups/GROUP_ID/polls \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Where?","options":["Paris","London"]}'

# Cast vote
curl -X POST http://localhost:5000/api/group/groups/GROUP_ID/polls/POLL_ID/vote \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"option":"Paris"}'
```

---

## 🐛 Known Issues

1. **Real-time updates** - Using polling, WebSockets planned
2. **Mobile app** - Web only, React Native planned
3. **Offline mode** - Not supported yet
4. **File attachments** - Itinerary photos not implemented
5. **Advanced polls** - Ranked choice voting not available

---

## 📋 Roadmap

- **Q1 2026**
  - ✅ Basic group management
  - ✅ Polls & voting
  - ✅ Itinerary builder
  - ✅ Expense integration

- **Q2 2026**
  - ⏳ Real-time updates (WebSockets)
  - ⏳ File attachments
  - ⏳ Advanced poll types
  - ⏳ Mobile app

- **Q3 2026**
  - ⏳ AI suggestions
  - ⏳ Smart itinerary builder
  - ⏳ Budget optimization
  - ⏳ Travel recommendations

---

## 📞 Support

- **Main Project:** [../../README.md](../../README.md)
- **Expense Engine:** [../expense_engine/README.md](../expense_engine/README.md)
- **Issues:** GitHub Issues
- **Email:** support@tripraft.com

---

**Built for travelers. Optimized for groups. 👥**
