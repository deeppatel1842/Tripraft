# Travel Planning Platform

A dynamic, scalable AI-powered travel planning platform built with React.js and Python/Flask.

## Features

- **Dynamic Branding** - Change your brand name and tagline via simple environment variables
- **Places Explorer** - AI-powered destination discovery with smart caching
- **Firebase Authentication** - Secure user authentication
- **Production-Ready** - Built for scale with rate limiting, connection pooling, and optimized caching
- **No Hardcoded Values** - Everything is configurable via `.env` files

## Quick Start

### 1. Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit with your values
nano .env  # or use your preferred editor
```

**Minimum required configuration:**
```bash
APP_NAME=YourBrandName
GOOGLE_API_KEY=your-google-api-key
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="your-private-key"
FIREBASE_CLIENT_EMAIL=your-email@project.iam.gserviceaccount.com
```

### 2. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd web/frontend
npm install
```

### 3. Run Development Servers

```bash
# Backend (Terminal 1)
cd web/backend
python app.py

# Frontend (Terminal 2)
cd web/frontend
npm run dev
```

Visit: **http://localhost:5173**

## Change Brand Name

Simply edit `.env`:
```bash
APP_NAME="My Travel App"
APP_DESCRIPTION="Plan amazing trips"
APP_TAGLINE="Adventure awaits"
```

Restart the backend server - done! Your new brand appears everywhere automatically.

## Architecture

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
