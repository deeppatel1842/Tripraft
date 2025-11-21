# TripRaft Places API

Professional Flask-based API for the TripRaft places database.

## Features

- **RESTful API** with proper HTTP methods and status codes
- **Pagination** for large result sets
- **Universal search** with relevance ranking
- **Error handling** with standardized responses
- **Input validation** and sanitization
- **CORS enabled** for frontend integration
- **Logging** with configurable levels
- **Thread-safe** database connections
- **Environment-based** configuration
- **No hardcoded values** - everything configurable

## Architecture

```
api/
├── app.py              # Flask application factory
├── run.py              # Application entry point
├── config/
│   ├── __init__.py
│   └── settings.py     # Configuration management
├── models/
│   ├── __init__.py
│   └── places.py       # Database models
├── routes/
│   ├── __init__.py
│   ├── countries.py    # Country endpoints
│   ├── states.py       # State endpoints
│   ├── cities.py       # City endpoints
│   └── places.py       # Places & search endpoints
└── utils/
    ├── __init__.py
    ├── database.py     # Database connection manager
    ├── validators.py   # Input validation
    └── responses.py    # Standardized responses
```

## API Endpoints

### Base URL
```
http://localhost:5000/api/v1
```

### Countries
- `GET /countries` - Get all countries
- `GET /countries/{country_id}` - Get specific country

### States
- `GET /states/{state_id}` - Get specific state
- `GET /states/country/{country_id}` - Get states by country

### Cities
- `GET /cities/{city_id}` - Get specific city
- `GET /cities/state/{state_id}` - Get cities by state
- `GET /cities/country/{country_id}` - Get cities by country

### Places
- `GET /places/{place_id}` - Get specific place
- `GET /places/city/{city_id}` - Get places by city (paginated)
- `GET /places/state/{state_id}` - Get places by state (paginated)
- `GET /places/country/{country_id}` - Get places by country (paginated)
- `GET /places/search?q=query` - Universal search (paginated)

### Pagination Parameters
- `limit` - Results per page (default: 50, max: 100)
- `offset` - Offset for pagination (default: 0)

## Response Format

### Success Response
```json
{
  "success": true,
  "message": "Retrieved 10 places",
  "data": [...],
  "pagination": {
    "total": 100,
    "limit": 10,
    "offset": 0,
    "count": 10,
    "has_more": true
  }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "data": null
}
```

## Installation

1. **Install dependencies:**
```bash
pip install flask flask-cors python-dotenv
```

2. **Configure environment:**
Edit `.env` file in `web/backend/`:
```env
FLASK_ENV=development
FLASK_PORT=5000
FLASK_DEBUG=True
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

3. **Run the server:**
```bash
cd web/backend
python api/run.py
```

## Testing the API

### Using curl:
```bash
# Get all countries
curl http://localhost:5000/api/v1/countries

# Get places in a city
curl http://localhost:5000/api/v1/places/city/los-angeles

# Search places
curl "http://localhost:5000/api/v1/places/search?q=museum&limit=10"

# With pagination
curl "http://localhost:5000/api/v1/places/city/new-york?limit=20&offset=0"
```

### Using browser:
```
http://localhost:5000/
http://localhost:5000/health
http://localhost:5000/api/v1/countries
```

## Configuration

All configuration is in `api/config/settings.py`:

- **Database paths** - Automatically resolved from project structure
- **CORS origins** - From environment variable
- **API prefix** - `/api/v1` (configurable)
- **Pagination limits** - Default: 50, Max: 100
- **Logging level** - From environment variable

## Development vs Production

### Development (default):
- Debug mode enabled
- Detailed error messages
- Hot reload on code changes

### Production:
Set in `.env`:
```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-production-secret-key
```

## Logging

Logs include:
- Request processing
- Database queries
- Errors with stack traces
- Performance metrics

Configure log level in `.env`:
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Error Handling

All endpoints handle:
- Invalid input validation
- Database connection errors
- Not found resources (404)
- Server errors (500)
- Proper error messages

## Security Features

- Input sanitization
- SQL injection prevention (parameterized queries)
- XSS protection
- CORS configuration
- Rate limiting ready (configurable)

## Performance

- Thread-safe database connections
- Connection pooling with context managers
- Efficient SQL queries with indexes
- Pagination for large datasets
- Ready for caching layer

## Next Steps

1. **Add caching** (Redis)
2. **Add rate limiting** (Flask-Limiter)
3. **Add authentication** (JWT)
4. **Add API documentation** (Swagger/OpenAPI)
5. **Add monitoring** (Prometheus)
6. **Deploy to production** (Railway/Render/Fly.io)

## Support

For issues or questions, check the main project README or create an issue.
