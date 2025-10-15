# Quick Start Guide

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (optional, for caching)
- Google API Key (Places, Geocoding, Routes)
- Firebase project (for authentication)

### Backend Setup

1. **Clone the repository**
   ```bash
   cd web/backend
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r ../../requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp ../../.env.example ../../.env
   # Edit .env with your values (API keys, brand name, etc.)
   ```

5. **Start development server**
   ```bash
   python app.py
   ```

   Backend will run on `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd web/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment** (optional)
   ```bash
   cp .env.example .env
   # Edit if you want to override backend config
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

   Frontend will run on `http://localhost:5173`

---

## Configuration

### Minimum Required Configuration

Edit `.env` in the project root:

```bash
# Brand Name (change this!)
APP_NAME=YourBrandName

# Google API Key (required)
GOOGLE_API_KEY=your-google-api-key

# Firebase Configuration (required for auth)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-email@project.iam.gserviceaccount.com
# ... (see .env.example for all Firebase fields)

# Redis (optional, uses in-memory cache if not available)
REDIS_URL=redis://localhost:6379/0
```

### Change Brand Name

Simply edit `.env`:
```bash
APP_NAME="My Travel App"
APP_DESCRIPTION="Plan amazing trips"
APP_TAGLINE="Adventure awaits"
```

Restart the backend server, and the new name will appear everywhere automatically.

---

## Project Structure

```
Travel/
├── .env                           # Configuration (DO NOT COMMIT)
├── .env.example                   # Configuration template
├── requirements.txt               # Python dependencies
├── global_config.py               # Legacy config (deprecated)
│
├── web/
│   ├── backend/
│   │   ├── app.py                # Main Flask application
│   │   ├── config.py             # Configuration loader
│   │   ├── gunicorn_config.py    # Production server config
│   │   ├── redis_config.py       # Redis configuration
│   │   ├── rate_limiter.py       # API rate limiting
│   │   │
│   │   ├── main_engine/
│   │   │   ├── main_engine.py    # Places search engine
│   │   │   └── trip_planner.py   # Trip planning logic
│   │   │
│   │   ├── database/
│   │   │   └── adaptive_database/
│   │   │       └── hubs/         # Cached places data
│   │   │
│   │   └── services/
│   │       └── firebase/         # Firebase authentication
│   │
│   └── frontend/
│       ├── src/
│       │   ├── config/
│       │   │   └── globalConfig.js  # Frontend config
│       │   │
│       │   ├── components/
│       │   │   ├── layout/
│       │   │   │   ├── Header.jsx   # Dynamic brand in header
│       │   │   │   └── Footer.jsx   # Dynamic brand in footer
│       │   │   │
│       │   │   └── animation/
│       │   │       └── AnimatedBackground.jsx
│       │   │
│       │   └── App.jsx
│       │
│       ├── .env.example          # Frontend config template
│       └── package.json
│
└── docs/
    ├── CONFIGURATION_GUIDE.md    # Full configuration guide
    └── QUICK_START.md            # This file
```

---

## API Endpoints

### Public Endpoints

- `GET /api/health` - Health check
- `GET /api/config` - Get public configuration (brand name, etc.)

### Authentication

- `POST /api/auth/verify` - Verify Firebase token
  ```json
  {
    "idToken": "firebase-id-token"
  }
  ```

### Places

- `GET /api/places/search?city=San Diego` - Search places in a city
  ```json
  {
    "success": true,
    "city": "San Diego",
    "places": [...],
    "count": 50,
    "cache_hit": true
  }
  ```

### Protected Endpoints

Require `Authorization: Bearer <firebase-token>` header:

- `GET /api/profile` - Get user profile

---

## Development

### Run Backend

```bash
cd web/backend
python app.py
```

### Run Frontend

```bash
cd web/frontend
npm run dev
```

### Run Redis (if using caching)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
redis-server
```

---

## Production Deployment

### Option 1: Traditional Server

1. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit with production values
   ```

2. **Build frontend:**
   ```bash
   cd web/frontend
   npm run build
   ```

3. **Start backend with Gunicorn:**
   ```bash
   cd web/backend
   gunicorn -c gunicorn_config.py app:app
   ```

4. **Configure nginx:**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location /api/ {
           proxy_pass http://localhost:5000;
       }
       
       location / {
           root /path/to/web/frontend/dist;
           try_files $uri /index.html;
       }
   }
   ```

### Option 2: Docker

1. **Build and run:**
   ```bash
   docker-compose up -d
   ```

2. **Check logs:**
   ```bash
   docker-compose logs -f
   ```

---

## Scaling for Large Traffic

### Small (< 1,000 daily users)

Default configuration is fine. Consider these settings:

```bash
WORKERS=2
REDIS_MAX_CONNECTIONS=20
CACHE_TTL=604800  # 7 days
```

### Medium (1K - 10K daily users)

```bash
WORKERS=4
WORKER_THREADS=2
REDIS_MAX_CONNECTIONS=50
CACHE_TTL=604800
ENABLE_AGGRESSIVE_CACHING=True
```

Recommended:
- Use separate Redis server
- Enable Redis persistence
- Monitor with basic tools

### Large (10K - 100K daily users)

```bash
WORKERS=8
WORKER_THREADS=4
REDIS_MAX_CONNECTIONS=100
CACHE_TTL=604800
ENABLE_AGGRESSIVE_CACHING=True
```

Recommended:
- Load balancer (nginx)
- Multiple application servers
- Redis Cluster or Sentinel
- CDN for static assets
- Monitoring (Prometheus, Grafana)

### Very Large (100K+ daily users)

```bash
WORKERS=16
WORKER_THREADS=4
REDIS_MAX_CONNECTIONS=200
REDIS_USE_CLUSTER=True
```

Recommended:
- Horizontal scaling (10+ servers)
- Redis Cluster
- CDN with edge caching
- Advanced monitoring and alerting
- Auto-scaling groups
- Database read replicas

---

## Common Tasks

### Change Brand Name

```bash
# Edit .env
APP_NAME="New Brand"

# Restart backend
python app.py  # Dev
# or
sudo systemctl restart yourapp  # Production
```

### Update Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd web/frontend
npm install
```

### Clear Cache

```bash
# Redis
redis-cli FLUSHALL

# Or via Python
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); r.flushall()"
```

### View Logs

```bash
# Development
tail -f logs/app.log

# Production (systemd)
sudo journalctl -u yourapp -f

# Docker
docker-compose logs -f
```

---

## Troubleshooting

### Backend won't start

1. Check Python version: `python --version` (need 3.11+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check `.env` file exists and has required values
4. Check port 5000 is not in use: `lsof -i :5000`

### Frontend won't start

1. Check Node version: `node --version` (need 18+)
2. Install dependencies: `npm install`
3. Check port 5173 is not in use

### Brand name not changing

1. Verify `APP_NAME` in `.env`
2. Restart backend server
3. Clear browser cache (Ctrl+Shift+R)
4. Check `/api/config` endpoint returns new name

### API errors

1. Check Google API key is valid
2. Verify APIs are enabled in Google Cloud Console
3. Check rate limits haven't been exceeded
4. Review logs for detailed errors

---

## Getting Help

1. **Check documentation:**
   - `docs/CONFIGURATION_GUIDE.md` - Full configuration reference
   - `docs/PROJECT_ARCHITECTURE.md` - System architecture
   - `.env.example` - All configuration options

2. **Enable debug mode:**
   ```bash
   FLASK_DEBUG=True
   ENABLE_DEBUG_MODE=True
   ```

3. **Check logs:**
   ```bash
   tail -f logs/app.log
   ```

4. **Test endpoints:**
   ```bash
   curl http://localhost:5000/api/health
   curl http://localhost:5000/api/config
   ```

---

**Ready to start? Run the development servers and visit http://localhost:5173**

Happy coding! 🚀
