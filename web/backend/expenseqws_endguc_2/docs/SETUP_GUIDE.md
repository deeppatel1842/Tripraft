# 🚀 Setup & Deployment Guide - Expense Engine

**Version:** 1.0.0  
**Audience:** Developers, DevOps Engineers

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Redis Configuration](#redis-configuration)
6. [Backend Deployment](#backend-deployment)
7. [Frontend Deployment](#frontend-deployment)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)

---

## 1️⃣ Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.9+ | Backend runtime |
| **Node.js** | 16+ | Frontend build tools |
| **Redis** | 6.0+ | Caching layer |
| **Git** | Any | Version control |
| **Firebase CLI** | Latest | Firebase deployment |

### Required Accounts

- **Firebase Account** (free tier works for development)
- **Redis Cloud Account** (optional, can use local Redis)
- **SMTP Provider** (Gmail, SendGrid, or similar for emails)

### System Requirements

**Development:**
- RAM: 4GB minimum, 8GB recommended
- Disk: 2GB free space
- OS: Windows 10+, macOS 10.15+, or Linux

**Production:**
- RAM: 2GB minimum per instance
- CPU: 2 cores minimum
- Disk: 10GB SSD recommended

---

## 2️⃣ Local Development Setup

### Step 1: Clone Repository

```powershell
# Clone the repository
git clone https://github.com/your-org/expense-engine.git
cd expense-engine
```

### Step 2: Setup Python Virtual Environment

```powershell
# Create virtual environment
python -m venv wayfinder

# Activate virtual environment
# Windows PowerShell:
.\wayfinder\Scripts\Activate.ps1

# Windows CMD:
.\wayfinder\Scripts\activate.bat

# Linux/Mac:
source wayfinder/bin/activate

# Verify activation (should show virtual env name in prompt)
```

### Step 3: Install Backend Dependencies

```powershell
# Navigate to backend directory
cd web/backend

# Install Python packages
pip install -r requirements.txt

# Verify installation
pip list
```

**Key Dependencies Installed:**
- `flask` - Web framework
- `firebase-admin` - Firestore and Auth SDK
- `redis` - Redis client
- `python-dotenv` - Environment variables
- `flask-cors` - CORS handling
- `gunicorn` - Production WSGI server

### Step 4: Install Frontend Dependencies

```powershell
# Navigate to frontend directory
cd ../frontend

# Install Node packages
npm install

# Verify installation
npm list --depth=0
```

**Key Dependencies Installed:**
- `react` - UI library
- `@tanstack/react-query` - Data fetching and caching
- `axios` - HTTP client
- `lucide-react` - Icon library
- `vite` - Build tool

---

## 3️⃣ Environment Configuration

### Backend Configuration

Create `.env` file in `web/backend/`:

```bash
# =============================================
# FIREBASE CONFIGURATION
# =============================================
# Path to your Firebase service account JSON file
FIREBASE_CREDENTIALS_PATH=./firebase-adminsdk-key.json

# Firebase project ID
FIREBASE_PROJECT_ID=your-project-id

# =============================================
# REDIS CONFIGURATION
# =============================================
# Local Redis (Development)
REDIS_URL=redis://localhost:6379/0

# Redis Cloud (Production)
# REDIS_URL=rediss://default:password@redis-12345.cloud.redislabs.com:12345

# Redis connection pool settings
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=2
REDIS_SOCKET_CONNECT_TIMEOUT=2

# =============================================
# EMAIL CONFIGURATION (Optional)
# =============================================
# SMTP server settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=True

# Email credentials
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password

# Sender information
EMAIL_FROM_ADDRESS=noreply@yourapp.com
EMAIL_FROM_NAME=Expense Engine

# =============================================
# APPLICATION SETTINGS
# =============================================
# Flask environment
FLASK_ENV=development
FLASK_DEBUG=True

# API base URL
API_BASE_URL=http://localhost:5001

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173

# Secret key for sessions (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your-secret-key-here

# =============================================
# RATE LIMITING
# =============================================
# Requests per minute per user
RATE_LIMIT_STANDARD=100
RATE_LIMIT_CREATE=30
RATE_LIMIT_DELETE=20
RATE_LIMIT_ADMIN=60

# =============================================
# CACHE CONFIGURATION
# =============================================
# Cache TTLs in seconds
CACHE_TTL_USER_PROFILE=3600        # 1 hour
CACHE_TTL_DISPLAY_NAME=3600        # 1 hour
CACHE_TTL_USER_GROUPS=1800         # 30 minutes
CACHE_TTL_GROUP_FULL=1800          # 30 minutes
CACHE_TTL_BALANCE=300              # 5 minutes
CACHE_TTL_INVITATIONS=600          # 10 minutes
CACHE_TTL_EXPENSES=900             # 15 minutes

# =============================================
# LOGGING
# =============================================
LOG_LEVEL=INFO
LOG_FILE=logs/expense_engine.log
```

### Frontend Configuration

Create `.env` file in `web/frontend/`:

```bash
# API endpoint
VITE_API_BASE_URL=http://localhost:5001/api/expense

# Firebase configuration (from Firebase Console > Project Settings > Web App)
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Environment
VITE_ENV=development

# Feature flags
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_ERROR_TRACKING=false
```

### Getting Firebase Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to **Project Settings** > **Service Accounts**
4. Click **Generate New Private Key**
5. Save the JSON file as `firebase-adminsdk-key.json` in `web/backend/`
6. Go to **Project Settings** > **General** > **Your Apps**
7. Add a web app and copy the config values to frontend `.env`

### Getting SMTP Credentials (Gmail Example)

1. Enable 2-factor authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Create a new app password for "Mail"
4. Use this password in `SMTP_PASSWORD` (not your regular password)

---

## 4️⃣ Database Setup

### Firestore Collections

The application will auto-create collections, but you can set them up manually:

```javascript
// Collections structure
expenses_app/
├── users/
│   └── {uid}/
├── groups/
│   └── {group_id}/
│       └── members/ (subcollection)
├── expenses/
│   └── {expense_id}/
│       └── splits/ (subcollection)
├── settlements/
│   └── {settlement_id}/
├── balances/
│   └── {group_id}/
├── invitations/
│   └── {invitation_id}/
├── idempotency_keys/
│   └── {key}/
└── audit_logs/
    └── {log_id}/
```

### Firestore Indexes

Create composite indexes for better query performance:

**File:** `web/backend/firestore.indexes.json`

```json
{
  "indexes": [
    {
      "collectionGroup": "expenses",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "group_id", "order": "ASCENDING" },
        { "fieldPath": "date", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "expenses",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "paid_by_uid", "order": "ASCENDING" },
        { "fieldPath": "date", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "invitations",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "invited_uid", "order": "ASCENDING" },
        { "fieldPath": "status", "order": "ASCENDING" },
        { "fieldPath": "created_at", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "settlements",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "group_id", "order": "ASCENDING" },
        { "fieldPath": "payment_date", "order": "DESCENDING" }
      ]
    }
  ]
}
```

**Deploy indexes:**
```powershell
# Login to Firebase
firebase login

# Deploy indexes
firebase deploy --only firestore:indexes
```

### Firestore Security Rules

**File:** `web/backend/firestore.rules`

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }
    
    function isUser(uid) {
      return isAuthenticated() && request.auth.uid == uid;
    }
    
    function isGroupMember(groupId) {
      return isAuthenticated() && 
        exists(/databases/$(database)/documents/groups/$(groupId)/members/$(request.auth.uid));
    }
    
    // Users collection
    match /users/{uid} {
      allow read: if isAuthenticated();
      allow write: if isUser(uid);
    }
    
    // Groups collection
    match /groups/{groupId} {
      allow read: if isGroupMember(groupId);
      allow create: if isAuthenticated();
      allow update, delete: if isGroupMember(groupId);
      
      // Group members subcollection
      match /members/{memberId} {
        allow read: if isGroupMember(groupId);
        allow write: if isGroupMember(groupId);
      }
    }
    
    // Expenses collection
    match /expenses/{expenseId} {
      allow read: if isAuthenticated();
      allow create: if isAuthenticated();
      allow update, delete: if isAuthenticated();
      
      // Expense splits subcollection
      match /splits/{splitId} {
        allow read: if isAuthenticated();
        allow write: if isAuthenticated();
      }
    }
    
    // Settlements collection
    match /settlements/{settlementId} {
      allow read: if isAuthenticated();
      allow create: if isAuthenticated();
      allow update, delete: if isAuthenticated();
    }
    
    // Balances collection
    match /balances/{groupId} {
      allow read: if isGroupMember(groupId);
      allow write: if isAuthenticated();
    }
    
    // Invitations collection
    match /invitations/{invitationId} {
      allow read: if isAuthenticated();
      allow create: if isAuthenticated();
      allow update: if isAuthenticated();
    }
    
    // Audit logs (read-only for users)
    match /audit_logs/{logId} {
      allow read: if isAuthenticated();
      allow write: if false; // Only backend can write
    }
  }
}
```

**Deploy rules:**
```powershell
firebase deploy --only firestore:rules
```

---

## 5️⃣ Redis Configuration

### Option 1: Local Redis (Development)

**Windows:**
```powershell
# Install using Chocolatey
choco install redis-64

# Or download MSI installer from:
# https://github.com/microsoftarchive/redis/releases

# Start Redis server
redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

**macOS:**
```bash
# Install using Homebrew
brew install redis

# Start Redis
brew services start redis

# Test connection
redis-cli ping
```

**Linux (Ubuntu):**
```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test connection
redis-cli ping
```

### Option 2: Redis Cloud (Production)

1. Go to [Redis Cloud](https://redis.com/try-free/)
2. Create a free account
3. Create a new database
4. Copy the connection string (rediss://...)
5. Update `REDIS_URL` in backend `.env`

**Free tier includes:**
- 30MB storage
- Enough for 1000-5000 active users
- Automatic backups
- SSL/TLS encryption

### Verify Redis Connection

```powershell
# From backend directory
cd web/backend

# Activate virtual environment
.\..\..\wayfinder\Scripts\Activate.ps1

# Test Redis connection
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"
# Should print: True
```

---

## 6️⃣ Backend Deployment

### Development Server

```powershell
# Navigate to backend directory
cd web/backend

# Activate virtual environment
.\..\..\wayfinder\Scripts\Activate.ps1

# Run Flask development server
python run.py

# Server starts at: http://localhost:5001
```

**Console output:**
```
 * Serving Flask app 'run'
 * Debug mode: on
 * Running on http://127.0.0.1:5001
 * Redis connected: True
 * Firestore connected: True
```

### Production Server (Gunicorn)

```bash
# Install gunicorn (should be in requirements.txt)
pip install gunicorn

# Run with 4 worker processes
gunicorn --bind 0.0.0.0:5001 \
         --workers 4 \
         --worker-class sync \
         --timeout 120 \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         --log-level info \
         run:app
```

**Systemd Service File (Linux):**

Create `/etc/systemd/system/expense-backend.service`:

```ini
[Unit]
Description=Expense Engine Backend
After=network.target redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/expense-engine/web/backend
Environment="PATH=/var/www/expense-engine/wayfinder/bin"
ExecStart=/var/www/expense-engine/wayfinder/bin/gunicorn \
          --bind 0.0.0.0:5001 \
          --workers 4 \
          --worker-class sync \
          --timeout 120 \
          run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl start expense-backend
sudo systemctl enable expense-backend
sudo systemctl status expense-backend
```

---

## 7️⃣ Frontend Deployment

### Development Server

```powershell
# Navigate to frontend directory
cd web/frontend

# Install dependencies (if not done)
npm install

# Start development server
npm run dev

# Server starts at: http://localhost:5173
```

### Production Build

```powershell
# Build for production
npm run build

# Output in: web/frontend/dist/
```

**Build output:**
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── [images/fonts]
└── favicon.ico
```

### Deploy to Hosting Providers

#### Option 1: Firebase Hosting

```powershell
# Install Firebase CLI (if not installed)
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize hosting
firebase init hosting
# Select: Use existing project
# Public directory: dist
# Single-page app: Yes
# Automatic builds: No

# Deploy
firebase deploy --only hosting

# Your app is live at: https://your-project.web.app
```

#### Option 2: Vercel

```powershell
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel deploy --prod

# Follow prompts to link project
```

#### Option 3: Netlify

```powershell
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist

# Follow prompts to link site
```

#### Option 4: Traditional Web Server (NGINX)

```nginx
# /etc/nginx/sites-available/expense-engine

server {
    listen 80;
    server_name your-domain.com;
    root /var/www/expense-engine/web/frontend/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;
    gzip_min_length 1000;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # React Router support (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional, if backend on same server)
    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/expense-engine /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8️⃣ Production Deployment

### Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Firebase project set up with production credentials
- [ ] Redis instance provisioned (Redis Cloud or self-hosted)
- [ ] SMTP configured for email notifications
- [ ] Firestore indexes deployed
- [ ] Firestore security rules deployed
- [ ] SSL certificate configured (Let's Encrypt recommended)
- [ ] Domain DNS configured
- [ ] Backend tested with `pytest` (if tests exist)
- [ ] Frontend built without errors
- [ ] Rate limiting tested
- [ ] Monitoring configured (optional: Sentry, DataDog)

### Deployment Architecture

```
[Users] --> [CloudFlare CDN] --> [Frontend (Firebase Hosting/Vercel)]
                                         |
                                         v
                                  [API Gateway]
                                         |
                                         v
                            [Load Balancer (NGINX/AWS ALB)]
                                    /    |    \
                                   /     |     \
                            [Backend] [Backend] [Backend]
                                   \     |     /
                                    \    |    /
                                   [Redis Cluster]
                                         |
                                   [Firestore]
```

### Environment-Specific Configuration

**Development:**
```bash
FLASK_ENV=development
FLASK_DEBUG=True
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
```

**Staging:**
```bash
FLASK_ENV=staging
FLASK_DEBUG=False
REDIS_URL=rediss://staging-redis.cloud.redislabs.com:12345
LOG_LEVEL=INFO
```

**Production:**
```bash
FLASK_ENV=production
FLASK_DEBUG=False
REDIS_URL=rediss://prod-redis.cloud.redislabs.com:12345
LOG_LEVEL=WARNING
SENTRY_DSN=https://your-sentry-dsn
```

### Health Checks & Monitoring

**Health check endpoint:**
```bash
curl http://localhost:5001/api/expense/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T21:00:00.123Z",
  "version": "1.0.0"
}
```

**Detailed health check:**
```bash
curl http://localhost:5001/api/expense/health/detailed
```

**Set up monitoring:**
```bash
# Install monitoring tools
pip install sentry-sdk python-datadog

# Add to run.py:
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FlaskIntegration()],
    environment=os.getenv("FLASK_ENV", "production"),
    traces_sample_rate=0.1
)
```

---

## 9️⃣ Troubleshooting

### Backend Issues

#### Issue: "ModuleNotFoundError: No module named 'firebase_admin'"

**Solution:**
```powershell
# Ensure virtual environment is activated
.\wayfinder\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

---

#### Issue: "Redis connection refused"

**Solution:**
```powershell
# Check if Redis is running
redis-cli ping

# If not running, start Redis
# Windows:
redis-server

# Linux/Mac:
brew services start redis  # macOS
sudo systemctl start redis-server  # Linux

# Check Redis URL in .env
# Should be: redis://localhost:6379/0
```

---

#### Issue: "Firebase permissions denied"

**Solution:**
1. Check `firebase-adminsdk-key.json` exists in `web/backend/`
2. Verify `FIREBASE_CREDENTIALS_PATH` in `.env` is correct
3. Ensure Firebase service account has correct permissions:
   - Go to Firebase Console > Project Settings > Service Accounts
   - Ensure service account has "Editor" or "Owner" role

---

#### Issue: "CORS errors in browser"

**Solution:**
Update `web/backend/config.py`:
```python
CORS_ORIGINS = [
    "http://localhost:5173",  # Development
    "https://your-domain.com"  # Production
]
```

Restart backend server.

---

### Frontend Issues

#### Issue: "npm install fails"

**Solution:**
```powershell
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json

# Reinstall
npm install
```

---

#### Issue: "Vite build fails with memory error"

**Solution:**
```powershell
# Increase Node memory limit
$env:NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

---

#### Issue: "API calls fail with 'Network Error'"

**Solution:**
1. Check `VITE_API_BASE_URL` in `.env` is correct
2. Ensure backend is running: `curl http://localhost:5001/api/expense/health`
3. Check browser console for CORS errors
4. Verify Firebase authentication token is valid

---

### Database Issues

#### Issue: "Firestore permission denied"

**Solution:**
Deploy security rules:
```powershell
firebase deploy --only firestore:rules
```

Or temporarily (development only):
```javascript
// In Firestore Console > Rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

---

#### Issue: "Firestore queries slow"

**Solution:**
Deploy indexes:
```powershell
firebase deploy --only firestore:indexes
```

Check Firestore Console > Indexes for missing composite indexes.

---

### Redis Issues

#### Issue: "Redis memory usage growing"

**Solution:**
```bash
# Check memory usage
redis-cli info memory

# Check key count
redis-cli dbsize

# Flush all keys (⚠️ caution in production)
redis-cli flushall

# Or flush specific pattern
redis-cli --scan --pattern "user_groups:*" | xargs redis-cli del
```

---

#### Issue: "Cache not invalidating"

**Solution:**
1. Check logs for cache invalidation messages: `🔄 Invalidated cache...`
2. Verify correct cache key prefixes in `constants.py`
3. Restart backend to apply code changes
4. Manually clear problematic cache:
```python
redis-cli del "user_groups:USER123"
redis-cli del "user_groups:USER123_summary"
```

---

### Performance Issues

#### Issue: "API responses slow (> 200ms)"

**Diagnosis:**
```bash
# Check detailed health
curl http://localhost:5001/api/expense/health/detailed

# Check cache hit rate
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:5001/api/expense/cache/stats

# Check slow queries
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:5001/api/expense/metrics
```

**Solutions:**
1. Increase cache TTLs in `.env`
2. Add missing Firestore indexes
3. Enable Redis persistence for faster restarts
4. Add more gunicorn workers
5. Upgrade Redis instance size

---

### Email Issues

#### Issue: "Emails not sending"

**Solution:**
1. Check SMTP credentials in `.env`
2. For Gmail, ensure app-specific password is used (not regular password)
3. Check logs for email errors:
```powershell
# View logs
cat logs/expense_engine.log | Select-String "email"
```
4. Test SMTP connection:
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'app-password')
server.quit()
```

---

## 🆘 Getting Help

### Log Files

**Backend logs:**
```powershell
# View logs
cat web/backend/logs/expense_engine.log

# Follow logs (real-time)
Get-Content web/backend/logs/expense_engine.log -Wait -Tail 50

# Search logs
Select-String -Path web/backend/logs/expense_engine.log -Pattern "ERROR"
```

**Frontend logs:**
- Browser Console (F12)
- Network tab for API requests

### Debug Mode

Enable debug logging:

**Backend (.env):**
```bash
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

**Frontend:**
```javascript
// In src/api/client.js
axios.interceptors.request.use(request => {
  console.log('API Request:', request);
  return request;
});
```

### Contact & Support

- **Documentation:** `expense_docs/` folder
- **GitHub Issues:** [Create an issue](https://github.com/your-org/expense-engine/issues)
- **Email:** support@yourapp.com

---

**End of Setup Guide**

**Next Steps:**
1. Complete setup following steps above
2. Review Admin Guide for monitoring
3. Check API Reference for endpoint documentation
4. See Architecture Flows for system understanding
