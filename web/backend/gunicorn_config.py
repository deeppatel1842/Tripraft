# Gunicorn Configuration for Production
# This file configures the production WSGI server for high-traffic scenarios

import os
import multiprocessing

# =============================================================================
# SERVER SOCKET
# =============================================================================
bind = f"{os.getenv('FLASK_HOST', '0.0.0.0')}:{os.getenv('FLASK_PORT', '5000')}"
backlog = 2048

# =============================================================================
# WORKER PROCESSES
# =============================================================================
# Number of worker processes (CPU cores * 2 + 1 is recommended)
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker class - use 'sync' for CPU-bound, 'gevent' or 'eventlet' for I/O-bound
worker_class = os.getenv('WORKER_CLASS', 'sync')

# Number of threads per worker (only for 'gthread' worker_class)
threads = int(os.getenv('WORKER_THREADS', 2))

# Worker timeout in seconds
timeout = int(os.getenv('WORKER_TIMEOUT', 120))

# Maximum requests a worker will process before restarting (prevents memory leaks)
max_requests = int(os.getenv('MAX_REQUESTS_PER_WORKER', 1000))
max_requests_jitter = 50  # Randomize restart to avoid all workers restarting at once

# Worker graceful timeout
graceful_timeout = 30

# Keep alive for persistent connections
keepalive = 5

# =============================================================================
# LOGGING
# =============================================================================
accesslog = os.getenv('ACCESS_LOG', '-')  # '-' means stdout
errorlog = os.getenv('ERROR_LOG', '-')    # '-' means stderr
loglevel = os.getenv('LOG_LEVEL', 'info').lower()

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# =============================================================================
# PROCESS NAMING
# =============================================================================
proc_name = os.getenv('APP_NAME', 'TravelApp')

# =============================================================================
# SERVER MECHANICS
# =============================================================================
daemon = False  # Don't daemonize (let Docker/systemd handle this)
pidfile = None  # Let process manager handle PID
umask = 0
user = None     # Run as the user who starts gunicorn
group = None
tmp_upload_dir = None

# =============================================================================
# SECURITY
# =============================================================================
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# =============================================================================
# PRELOAD & RELOADING
# =============================================================================
# Preload application before forking workers (saves memory via copy-on-write)
preload_app = True

# Auto-reload on code changes (DISABLE in production!)
reload = os.getenv('FLASK_ENV', 'production') == 'development'

# =============================================================================
# HOOKS (for custom initialization)
# =============================================================================

def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"Starting {proc_name} with {workers} workers...")

def on_reload(server):
    """Called to recycle workers during a reload."""
    print("Reloading workers...")

def when_ready(server):
    """Called just after the server is started."""
    print(f"{proc_name} is ready to handle requests")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    print("Forking new master process...")

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    print(f"Worker received INT or QUIT signal (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    print(f"Worker received ABORT signal (pid: {worker.pid})")
