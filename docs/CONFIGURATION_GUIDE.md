# Configuration Guide

## Overview

This application uses a centralized configuration system with environment variables. All configuration is managed through `.env` files for easy deployment and brand customization.

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   ```bash
   # Change the brand name
   APP_NAME="YourBrandName"
   
   # Add your API keys
   GOOGLE_API_KEY="your-key-here"
   ```

3. **Start the application:**
   ```bash
   # Development
   cd web/backend
   python app.py
   
   # Production
   gunicorn -c gunicorn_config.py app:app
   ```

---

## Configuration Files

### Backend Configuration

#### `.env` (Root Level)
Main environment variables file. **DO NOT commit this file to git!**

#### `.env.example` (Root Level)
Template with all available configuration options and descriptions.

#### `web/backend/config.py`
Python configuration class that loads and validates environment variables.

#### `web/backend/gunicorn_config.py`
Production WSGI server configuration for high-traffic scenarios.

#### `web/backend/redis_config.py`
Redis caching configuration for scalability.

#### `web/backend/rate_limiter.py`
API rate limiting to prevent abuse.

### Frontend Configuration

#### `web/frontend/.env` (Not in git)
Frontend environment variables.

#### `web/frontend/.env.example`
Frontend configuration template.

#### `web/frontend/src/config/globalConfig.js`
JavaScript configuration that loads environment variables and fetches dynamic config from backend.

---

## Configuration Sections

### 1. Brand Configuration

**Change these to customize your brand:**

```bash
APP_NAME=YourBrandName
APP_DESCRIPTION=AI-powered travel planning platform
APP_TAGLINE=Discover. Plan. Explore.
```

These values will automatically update:
- Header logo text
- Footer branding
- Animated background
- Page titles
- API responses

### 2. Flask Configuration

```bash
SECRET_KEY=your-super-secret-key-change-in-production
FLASK_ENV=development  # or 'production'
FLASK_DEBUG=True       # False in production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

**Production Settings:**
```bash
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<generate-a-strong-random-key>
```

### 3. Google API Configuration

```bash
GOOGLE_API_KEY=your-google-api-key-here
```

Get your API key from: https://console.cloud.google.com/

**Required APIs:**
- Places API (New)
- Geocoding API
- Routes API

### 4. Firebase Configuration

```bash
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-email@project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
# ... (other Firebase fields)
```

Download service account JSON from Firebase Console and extract values.

### 5. Redis Configuration

```bash
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_HEALTH_CHECK_INTERVAL=30
```

**Production Redis URL Examples:**
```bash
# Self-hosted
REDIS_URL=redis://your-server:6379/0

# Redis Cloud
REDIS_URL=redis://default:password@your-instance.redislabs.com:6379

# AWS ElastiCache
REDIS_URL=redis://your-elasticache-endpoint:6379
```

### 6. API Rate Limiting

```bash
# Requests per second for Google Places API
PLACES_API_RATE_LIMIT=10

# Maximum concurrent API requests
MAX_CONCURRENT_REQUESTS=5

# Request timeout in seconds
API_REQUEST_TIMEOUT=30
```

**Adjust based on your Google API quota.**

### 7. Caching Strategy

```bash
# Cache TTL in seconds (604800 = 7 days)
CACHE_TTL=604800

# Enable aggressive caching for production
ENABLE_AGGRESSIVE_CACHING=True

# Cache warming on startup (pre-populate cache)
CACHE_WARMING_ENABLED=False
```

### 8. Performance & Scalability

```bash
# Number of worker processes
WORKERS=4

# Worker timeout in seconds
WORKER_TIMEOUT=120

# Maximum requests per worker before restart
MAX_REQUESTS_PER_WORKER=1000

# Enable threading
WORKER_THREADS=2
```

**Recommended Settings by Traffic:**

| Daily Users | Workers | Threads | Redis Max Connections |
|-------------|---------|---------|----------------------|
| < 1,000     | 2       | 2       | 20                   |
| 1K - 10K    | 4       | 2       | 50                   |
| 10K - 100K  | 8       | 4       | 100                  |
| 100K+       | 16+     | 4       | 200+                 |

### 9. CORS Configuration

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com
CORS_ALLOW_CREDENTIALS=True
```

**Production:** Add all your frontend domains.

### 10. Logging

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/app.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5      # Keep 5 old log files
```

### 11. Security

```bash
SESSION_COOKIE_SECURE=False  # True in production (requires HTTPS)
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
TOKEN_EXPIRY=3600  # 1 hour in seconds
```

### 12. Feature Flags

```bash
ENABLE_ANALYTICS=False
ENABLE_DEBUG_MODE=False
ENABLE_API_MONITORING=True
```

---

## Frontend Environment Variables

Create `web/frontend/.env`:

```bash
# Brand Configuration (optional, fetched from backend by default)
VITE_APP_NAME=YourBrandName

# API Configuration
VITE_API_BASE_URL=http://localhost:5000/api

# Production
# VITE_API_BASE_URL=https://api.yourdomain.com/api

# Feature Flags
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG_MODE=false
```

---

## Deployment Guides

### Development

```bash
# Backend
cd web/backend
python app.py

# Frontend
cd web/frontend
npm run dev
```

### Production (Single Server)

1. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   cd web/frontend && npm install && npm run build
   ```

3. **Start with Gunicorn:**
   ```bash
   cd web/backend
   gunicorn -c gunicorn_config.py app:app
   ```

4. **Use a reverse proxy (nginx):**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location /api/ {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location / {
           root /path/to/web/frontend/dist;
           try_files $uri $uri/ /index.html;
       }
   }
   ```

### Production (Docker)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment variables will be provided by docker-compose
ENV FLASK_ENV=production

# Run with gunicorn
CMD ["gunicorn", "-c", "web/backend/gunicorn_config.py", "web.backend.app:app"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

Run:
```bash
docker-compose up -d
```

---

## Changing Brand Name

### Method 1: Environment Variable (Recommended)

1. Edit `.env`:
   ```bash
   APP_NAME="NewBrandName"
   APP_DESCRIPTION="New description"
   APP_TAGLINE="New tagline"
   ```

2. Restart application:
   ```bash
   # Development
   Ctrl+C and restart
   
   # Production
   sudo systemctl restart yourapp
   # or
   docker-compose restart
   ```

3. Frontend will automatically fetch new brand name from backend API.

### Method 2: Frontend Override

Edit `web/frontend/.env`:
```bash
VITE_APP_NAME="NewBrandName"
```

Rebuild frontend:
```bash
cd web/frontend
npm run build
```

---

## Scaling for Large Traffic

### Horizontal Scaling

1. **Load Balancer** (nginx, HAProxy)
2. **Multiple Application Servers** (each running gunicorn)
3. **Centralized Redis** (Redis Cluster or Sentinel)
4. **CDN** for static assets

### Redis Scaling

**Option 1: Redis Sentinel (High Availability)**
```bash
REDIS_USE_SENTINEL=True
REDIS_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
REDIS_SENTINEL_MASTER=mymaster
```

**Option 2: Redis Cluster (Horizontal Scaling)**
```bash
REDIS_USE_CLUSTER=True
REDIS_CLUSTER_NODES=node1:6379,node2:6379,node3:6379
```

### Monitoring

- **Application Performance:** New Relic, DataDog, Sentry
- **Server Metrics:** Prometheus + Grafana
- **Logs:** ELK Stack (Elasticsearch, Logstash, Kibana)

---

## Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `FLASK_DEBUG=False` in production
- [ ] Use HTTPS and set `SESSION_COOKIE_SECURE=True`
- [ ] Restrict `CORS_ORIGINS` to your domains only
- [ ] Use environment-specific `.env` files (don't reuse dev keys)
- [ ] Enable Redis password authentication
- [ ] Use firewall to restrict Redis access
- [ ] Regularly rotate API keys
- [ ] Enable rate limiting
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated

---

## Troubleshooting

### Brand Name Not Updating

1. Check `.env` file has correct `APP_NAME`
2. Restart backend server
3. Clear browser cache
4. Check frontend is fetching from `/api/config` endpoint

### Redis Connection Errors

1. Check Redis is running: `redis-cli ping`
2. Verify `REDIS_URL` in `.env`
3. Check firewall allows connection
4. Increase `REDIS_MAX_CONNECTIONS` if pool exhausted

### High Memory Usage

1. Reduce `WORKERS` count
2. Lower `MAX_REQUESTS_PER_WORKER`
3. Enable `preload_app = True` in gunicorn
4. Optimize Redis memory with eviction policy

### Slow API Responses

1. Enable `ENABLE_AGGRESSIVE_CACHING=True`
2. Increase `REDIS_MAX_CONNECTIONS`
3. Add more workers: `WORKERS=<cpu_count * 2>`
4. Use Redis Cluster for distributed caching
5. Implement CDN for static assets

---

## Support

For issues or questions:
1. Check logs in `logs/app.log`
2. Enable debug mode temporarily: `FLASK_DEBUG=True`
3. Check configuration: `curl http://localhost:5000/api/config`

---

**Last Updated:** 2025-01-14
