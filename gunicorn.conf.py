# Gunicorn configuration for SABC Tournament Management System
import os

# Server socket
bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '8000')}"

# Worker processes
workers = int(os.environ.get("WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"

# Process naming
proc_name = "sabc-tournament"

# Worker timeout (30 seconds)
timeout = 30
keepalive = 2

# Restart workers after this many requests (helps prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100

# Preload app for better memory efficiency
preload_app = True

# Security
limit_request_line = 2048
limit_request_fields = 100
limit_request_field_size = 8192
