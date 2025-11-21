# Quick Start - Backend Only

**Simple command to run TripRaft backend**

---

## 🚀 Run Backend

```bash
cd web\backend
python run.py
```

That's it! ✅

---

## ✅ What's Running

- **Expense Management API** - Track expenses, split bills
- **Group Planner API** - Create trip groups, collaborate
- **Firebase Auth** - User authentication
- **Redis Cache** - Fast data caching

---

## 🌐 Access Points

**Health Check:**
```
http://localhost:5000/health
```

**API Root:**
```
http://localhost:5000/
```

**Expense API:**
```
http://localhost:5000/api/expense/*
```

**Group Planner:**
```
http://localhost:5000/api/groups/*
```

---

## 📋 Prerequisites

### 1. Activate Virtual Environment
```bash
cd C:\Users\Kashyap\Documents\Deep\Travel
.\wayfinder\Scripts\Activate.ps1
```

### 2. Install Requirements
```bash
cd web\backend
pip install -r requirements.txt
```

### 3. Configure Environment
Create `.env` in `web/backend/`:
```env
# Firebase
FIREBASE_PROJECT_ID=your-project
FIREBASE_PRIVATE_KEY="your-key"
FIREBASE_CLIENT_EMAIL=your-email

# Redis
REDIS_URL=redis://localhost:6379/0

# Server
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_ENV=development
```

### 4. Start Redis
```bash
# Make sure Redis is running on port 6379
redis-server
```

---

## ✅ Success Indicators

You'll see:
```
============================================================
🚀 TripRaft Backend Server
============================================================
Environment: development
Server: http://0.0.0.0:5000
Health Check: http://0.0.0.0:5000/health
============================================================

✅ Response compression enabled (gzip, level 6)
⚠️  Places database not found - Places API will not be available
Flask application created successfully
 * Running on http://0.0.0.0:5000
```

**Note:** The warning about places database is expected - we don't need it!

---

## 🧪 Test It Works

```bash
# Test health check
curl http://localhost:5000/health

# Should return:
# {
#   "status": "healthy",
#   "service": "TripRaft Backend",
#   "version": "1.0.0",
#   "features": ["expense_management", "group_planner"]
# }
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
netstat -ano | findstr :5000

# Kill it
taskkill /PID <process_id> /F

# Or change port in .env
FLASK_PORT=5001
```

### Redis Connection Error
```bash
# Start Redis
redis-server

# Or check Redis is running
redis-cli ping
# Should return: PONG
```

### Import Errors
```bash
# Make sure you're in virtual environment
.\wayfinder\Scripts\Activate.ps1

# Reinstall requirements
pip install -r requirements.txt
```

---

## 🔄 Full Development Setup

### With Frontend
```bash
# Terminal 1 - Backend
cd web\backend
python run.py

# Terminal 2 - Frontend
cd web\frontend
npm run dev
```

**Access:**
- Backend: http://localhost:5000
- Frontend: http://localhost:5173

---

*Quick Start Guide - TripRaft Backend*
