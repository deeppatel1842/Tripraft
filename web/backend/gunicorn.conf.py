"""
Gunicorn Configuration
Production server settings with graceful shutdown and worker recycling.

Start with:
    gunicorn -c gunicorn.conf.py "app.api.factory:create_app()"
"""
import multiprocessing
import os

# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------
workers = int(os.getenv('GUNICORN_WORKERS', min(multiprocessing.cpu_count() * 2 + 1, 9)))
threads = int(os.getenv('GUNICORN_THREADS', 2))
worker_class = 'gevent'               # Required for Flask-SocketIO

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
timeout = 120                          # Kill worker after 120s of no response
graceful_timeout = 30                  # Wait 30s for workers to finish on SIGTERM
keepalive = 5                          # Keep-alive connections for 5s

# ---------------------------------------------------------------------------
# Worker recycling (prevents memory leaks)
# ---------------------------------------------------------------------------
max_requests = 1000                    # Restart worker after 1000 requests
max_requests_jitter = 50               # Randomize to avoid thundering herd

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
accesslog = '-'                        # stdout
errorlog = '-'                         # stderr
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Disable default access log since middleware handles structured logging
access_log_format = None

# ---------------------------------------------------------------------------
# Process naming
# ---------------------------------------------------------------------------
proc_name = 'tripraft-api'

# ---------------------------------------------------------------------------
# Preloading
# ---------------------------------------------------------------------------
preload_app = True                     # Load app before forking workers

# ---------------------------------------------------------------------------
# Server hooks
# ---------------------------------------------------------------------------
def on_starting(server):
    """Called when the master process is starting."""
    server.log.info('TripRaft API starting (%d workers)', server.cfg.workers)


def post_fork(server, worker):
    """Called after a worker has been forked."""
    server.log.info('Worker %s spawned (pid: %s)', worker.age, worker.pid)


def worker_exit(server, worker):
    """Called when a worker exits."""
    server.log.info('Worker %s exited (pid: %s)', worker.age, worker.pid)


def on_exit(server):
    """Called when gunicorn master shuts down."""
    server.log.info('TripRaft API shutting down')
