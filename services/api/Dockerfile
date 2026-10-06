# Purpose: Builds the non-root Python API image and its production entry point.
# ============================================================
# TripRaft Backend — Production Dockerfile
# Multi-stage build for minimal image size
# ============================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

# Install system dependencies (for psycopg2, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Dependencies stage
# ---------------------------------------------------------------------------
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------
FROM base AS runtime

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r tripraft && useradd -r -g tripraft tripraft && \
    mkdir -p /app/catalog && \
    chown -R tripraft:tripraft /app
USER tripraft

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${FLASK_PORT:-5000}/api/health/live')" || exit 1

EXPOSE ${FLASK_PORT:-5000}

# Production server via gunicorn
ENTRYPOINT ["sh", "docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.core.factory:create_app()"]
