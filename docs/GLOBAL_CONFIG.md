# Global Config & No-Hardcode Guidelines

Keep all environment-specific values, secrets, and service endpoints out of source files.

- Backend: use `backend/config.py` which reads from environment variables (via `.env`).
- Frontend: expose runtime values via Vite env vars (prefix `VITE_`) and reference `frontend/src/config/globalConfig.js`.
- Cache: centralize cache logic in `cache/redis_client.py` and use `cache.redis_client.redis_client` from backend code.
- Services: add API client wrappers in `services/` and register them from a startup module if needed.
- Storage: add DB adapters under `storage/` to keep persistence concerns separated.

Pattern example (backend):

    from config import Config
    from cache.redis_client import redis_client

    app.config.from_object(Config)
    redis_client.init_app(app)
