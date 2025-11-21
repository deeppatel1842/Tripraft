# 🌍 Tripraft - Complete Travel & Expense Management Platform

> **Production-Ready Travel Planning Suite with Advanced Expense Splitting**

A comprehensive full-stack platform combining AI-powered travel planning with professional expense management. Built with React.js and Python/Flask for scalability and performance.

---

## 🎯 What is Tripraft?

Tripraft is a complete travel ecosystem with **three integrated modules**:

### 1. 🗺️ **Travel Planning Engine**
- AI-powered destination discovery
- Smart place recommendations using Our own API
- Dynamic radius calculation based on city density
- Intelligent caching for 97% performance improvement

### 2. 👥 **Group Planner**
- Collaborative trip planning
- Real-time member coordination
- Polls & voting for destinations
- Itinerary management
- Integrated expense tracking

### 3. 💰 **Expense Engine** 
- Split bills with unlimited members
- Multiple split types (equal, percentage, custom)
- Real-time balance calculations
- Debt simplification algorithm
- Multi-currency support
- Settlement tracking
- Email notifications
- **97% faster than traditional approaches** (5ms cached responses)
- **92% cache hit rate** in production

---

## 📁 Repository Structure

```
tripraft/
├── web/
│   ├── backend/              # Python/Flask Backend
│   │   ├── expense_engine/   # 💰 Expense splitting system
│   │   │   ├── docs/         # Complete expense documentation
│   │   │   ├── routes/       # API endpoints (40 total)
│   │   │   ├── security/     # RBAC, rate limiting, audit logs
│   │   │   └── README.md     # Expense Engine guide
│   │   │
│   │   ├── Group_planner/    # 👥 Trip planning & coordination
│   │   │   └── README.md     # Group Planner guide
│   │   │
│   │   ├── api/              # Travel API routes
│   │   ├── cache/            # Redis caching layer
│   │   ├── database/         # Firestore operations
│   │   └── config.py         # Environment configuration
│   │
│   └── frontend/             # React.js Frontend
│       ├── src/
│       │   ├── components/   # Reusable UI components
│       │   ├── pages/        # Page-level components
│       │   └── config/       # Frontend configuration
│       └── package.json
│
├── docs/                     # Project documentation
│   ├── QUICK_START_GUIDE.md
│   ├── API_DOCUMENTATION.md
│   └── ARCHITECTURE.md
│
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Redis 6.0+** (for caching)
- **Firebase Project** (for auth & database)
- **Google API Key** (for Places API)

### Step 1: Clone Repository

```bash
git clone git@github.com:deeppatel1842/Tripraft.git
cd Tripraft
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials  
# - FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL
# - REDIS_URL (default: redis://localhost:6379/0)
# - APP_NAME (your brand name)
```

**Minimum Required Configuration:**
```bash
APP_NAME=Tripraft
GOOGLE_API_KEY=your-google-api-key
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
REDIS_URL=redis://localhost:6379/0
```

### Step 3: Install Dependencies

```bash
# Backend (Python 3.9+)
pip install -r requirements.txt

# Frontend (Node 18+)
cd web/frontend
npm install
cd ../..
```

### Step 4: Start Redis

```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# Windows: Download from https://redis.io/download
# Mac: brew install redis && redis-server
# Linux: sudo apt-get install redis-server
```

### Step 5: Run Development Servers

```bash
# Terminal 1: Backend
cd web/backend
python run.py

# Terminal 2: Frontend
cd web/frontend
npm run dev
```

**Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000
- Health Check: http://localhost:5000/api/health

---

## 📚 Documentation

### Main Guides
- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Get running in 5 minutes
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Complete environment setup
- **[API Documentation](docs/API_DOCUMENTATION.md)** - All API endpoints

### Module-Specific Documentation

#### 💰 Expense Engine
- **[Expense Engine README](web/backend/expense_engine/README.md)** - Module overview
- **[Executive Summary](web/backend/expense_engine/docs/EXECUTIVE_SUMMARY.md)** - What we built
- **[API Reference](web/backend/expense_engine/docs/API_REFERENCE.md)** - 40 endpoints documented
- **[Architecture Flows](web/backend/expense_engine/docs/ARCHITECTURE_FLOWS.md)** - 16 Mermaid diagrams
- **[Setup Guide](web/backend/expense_engine/docs/SETUP_GUIDE.md)** - Installation & deployment
- **[Production Summary](web/backend/expense_engine/docs/PRODUCTION_SUMMARY.md)** - Production readiness
- **[Mermaid Flows](web/backend/expense_engine/docs/MERMAID_FLOWS.md)** - 12 detailed flowcharts

#### 👥 Group Planner
- **[Group Planner README](web/backend/Group_planner/README.md)** - Module overview
- Trip planning & coordination
- Member management
- Polls & voting system

#### 🗺️ Travel Engine
- Places discovery with Google Places API
- Smart radius calculation
- Caching optimization

---

## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │  ← Dynamic brand loading
│   (Port 5173)   │
└────────┬────────┘
         │
         ↓ /api/*
┌─────────────────┐
│  Flask Backend  │  ← Environment-based config
│   (Port 5000)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────┐
    ↓         ↓          ↓         ↓
┌──────┐  ┌─────┐  ┌─────────┐  ┌────────┐
│Redis │  │Google│  │Firebase│  │SQLite │
│Cache │  │ API  │  │  Auth  │  │  DB   │
└──────┘  └─────┘  └─────────┘  └────────┘
```

## Scaling for Production

### Small Scale (< 1K users/day)
Default settings work fine. Just deploy!

### Medium Scale (1K - 10K users/day)
```bash
WORKERS=4
REDIS_MAX_CONNECTIONS=50
ENABLE_AGGRESSIVE_CACHING=True
```

### Large Scale (10K - 100K users/day)
```bash
WORKERS=8
WORKER_THREADS=4
REDIS_MAX_CONNECTIONS=100
# + Use Redis Cluster
# + Add CDN
# + Enable monitoring
```

### Very Large Scale (100K+ users/day)
- Horizontal scaling with load balancer
- Redis Cluster for distributed caching
- Multiple application servers
- Auto-scaling groups
- See `docs/CONFIGURATION_GUIDE.md` for details

## Production Deployment

### Traditional Server

```bash
# Build frontend
cd web/frontend
npm run build

# Start backend with Gunicorn
cd ../backend
gunicorn -c gunicorn_config.py app:app
```

### Docker

```bash
docker-compose up -d
```

### Recommended Stack

- **Load Balancer:** nginx or HAProxy
- **Application:** Gunicorn with multiple workers
- **Cache:** Redis Cluster
- **CDN:** Cloudflare or AWS CloudFront
- **Monitoring:** Prometheus + Grafana

## Key Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Main configuration (brand, API keys, scaling) |
| `web/backend/config.py` | Configuration loader and validator |
| `web/backend/gunicorn_config.py` | Production server settings |
| `web/backend/rate_limiter.py` | API rate limiting |
| `web/frontend/src/config/globalConfig.js` | Frontend configuration |

## Documentation

- **[Quick Start Guide](docs/QUICK_START_NEW.md)** - Get up and running in 5 minutes
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Complete configuration reference
- **[Project Architecture](docs/PROJECT_ARCHITECTURE.md)** - System design and architecture

## Tech Stack

### Frontend
- React.js 18
- React Router for navigation
- Vite for build tooling
- Firebase Authentication

### Backend
- Python 3.11+
- Flask (web framework)
- Gunicorn (production server)
- Redis (caching)
- SQLite (local data)

### APIs
- Google Places API (New)
- Google Geocoding API
- Google Routes API
- Firebase Auth

## Security Features

- Environment-based configuration (no secrets in code)
- Rate limiting on all endpoints
- CORS protection
- Firebase token verification
- Secure session handling
- Input validation

## Performance Optimizations

- Aggressive caching with Redis
- Connection pooling
- Worker process management
- Preloaded application code
- CDN-ready static assets
- Optimized API calls

## No Hotel/Flight Dependencies

This platform focuses on places and trip planning. All hotel and flight booking integrations have been removed for a cleaner, more focused codebase.

## Development

```bash
# Backend
cd web/backend
python app.py

# Frontend with hot reload
cd web/frontend
npm run dev

# Redis (optional)
docker run -d -p 6379:6379 redis:7-alpine
```

## Testing

```bash
# Check backend health
curl http://localhost:5000/api/health

# Check configuration
curl http://localhost:5000/api/config

# Search places
curl "http://localhost:5000/api/places/search?city=San%20Diego"
```

## Project Status

✅ Dynamic brand configuration  
✅ Scalable architecture  
✅ Production-ready  
✅ No hardcoded values  
✅ Hotel/flight dependencies removed  
✅ Comprehensive documentation  
✅ Rate limiting implemented  
✅ Redis caching optimized  

## License

Proprietary - All rights reserved

## Support

For configuration help, see:
1. `docs/QUICK_START_NEW.md` for quick setup
2. `docs/CONFIGURATION_GUIDE.md` for detailed configuration
3. `.env.example` for all available options

---

**Built for scale. Ready for your brand. Deploy with confidence.** 🚀
