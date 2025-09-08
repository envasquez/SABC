import os

bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"
proc_name = "sabc-tournament"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
limit_request_line = 2048
limit_request_fields = 100
limit_request_field_size = 8192
