# Monitoring & Observability - SABC Application

This document describes the monitoring and observability infrastructure for the SABC tournament management application.

## Overview

Phase 3 implementation includes:
- **Sentry**: Centralized error tracking and performance monitoring
- **Prometheus**: Application metrics collection and monitoring
- **Automatic instrumentation**: Request tracking and performance metrics

## Sentry Error Monitoring

### Setup

Sentry is integrated but **disabled by default**. To enable:

```bash
# Set the Sentry DSN environment variable
export SENTRY_DSN="https://your-key@sentry.io/your-project-id"

# Optional: Set release version for deployment tracking
export RELEASE_VERSION="v1.2.3"
```

### Features

- **Automatic error capture**: Unhandled exceptions are sent to Sentry
- **Request context**: Full HTTP request details (with sensitive data filtered)
- **Performance monitoring**: 10% of transactions sampled in production
- **Database monitoring**: SQLAlchemy query performance tracking
- **Privacy-first**: Sensitive data (passwords, tokens, cookies) automatically filtered

### Configuration

```python
# Environment variables
SENTRY_DSN=<your-sentry-dsn>           # Required to enable Sentry
ENVIRONMENT=production|development     # Controls sampling rate
RELEASE_VERSION=v1.0.0                 # Optional deployment tracking
```

### Trace Sampling Rates

- **Production**: 10% of requests (reduces overhead and costs)
- **Development/Test**: 0% (no performance data collected)

### Sensitive Data Filtering

The following data is automatically removed before sending to Sentry:
- HTTP Headers: `authorization`, `cookie`, `x-csrf-token`
- Query strings (may contain tokens)
- Form data (may contain passwords)
- Environment variables: `DATABASE_URL`, `SECRET_KEY`, `SENTRY_DSN`, `SMTP_PASSWORD`

## Prometheus Metrics

### Metrics Endpoint

```
GET /metrics
```

Returns metrics in Prometheus text format for scraping.

**Important**: This endpoint should be restricted by firewall/network rules in production to prevent unauthorized access.

### Available Metrics

#### HTTP Request Metrics

```
http_requests_total{method, endpoint, status}
  - Counter: Total HTTP requests
  - Labels: method, endpoint, status code

http_request_duration_seconds{method, endpoint}
  - Histogram: Request latency distribution
  - Buckets: 0.01s to 10s
  - Labels: method, endpoint
```

#### Database Metrics

```
db_query_duration_seconds{query_type}
  - Histogram: Database query latency
  - Buckets: 0.001s to 5s

db_connections_active
  - Gauge: Current active database connections
```

#### Application Metrics

```
active_sessions
  - Gauge: Number of active user sessions

poll_votes_total{poll_type}
  - Counter: Total poll votes submitted

failed_logins_total
  - Counter: Total failed login attempts

email_sent_total{email_type, status}
  - Counter: Total emails sent (success/failure)
```

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'sabc-app'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Example queries for dashboards:

**Request Rate**:
```
rate(http_requests_total[5m])
```

**Request Latency (p95)**:
```
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error Rate**:
```
rate(http_requests_total{status=~"5.."}[5m])
```

**Failed Login Rate**:
```
rate(failed_logins_total[5m])
```

## Usage in Code

### Tracking Custom Metrics

```python
from core.monitoring.metrics import poll_votes_total, failed_logins_total

# Increment poll vote counter
poll_votes_total.labels(poll_type="tournament_location").inc()

# Increment failed login counter
failed_logins_total.inc()
```

### Tracking Database Queries

```python
from core.monitoring.metrics import db_query_duration_seconds
import time

start = time.time()
# ... database query ...
duration = time.time() - start
db_query_duration_seconds.labels(query_type="select").observe(duration)
```

### Manual Sentry Error Reporting

```python
import sentry_sdk

# Capture exception with context
try:
    # ... code ...
except Exception as e:
    sentry_sdk.capture_exception(e)

# Add custom context
with sentry_sdk.configure_scope() as scope:
    scope.set_tag("poll_id", poll.id)
    scope.set_user({"id": user.id, "email": user.email})
```

## Alerting Recommendations

### Sentry Alerts

Configure alerts for:
- Any error with rate > 10/minute
- Database connection failures
- Email sending failures
- New error types (first-time occurrences)

### Prometheus/Grafana Alerts

Configure alerts for:
- Request error rate > 5%
- Request latency p95 > 1 second
- Failed login rate > 50/minute (potential attack)
- Database query latency p95 > 100ms
- Active database connections > 80% of pool size

## Monitoring Best Practices

1. **Review Sentry daily**: Check for new or recurring errors
2. **Monitor dashboards**: Watch for performance degradation
3. **Set up alerts**: Don't rely on manual checking
4. **Track deployments**: Use RELEASE_VERSION for deployment tracking
5. **Analyze slow queries**: Use db_query_duration metrics
6. **Monitor user activity**: Track poll votes, logins, email sends

## Troubleshooting

### Sentry Not Capturing Errors

1. Check SENTRY_DSN is set: `echo $SENTRY_DSN`
2. Check logs for Sentry initialization
3. Verify DSN is valid in Sentry dashboard
4. Check error filters aren't too aggressive

### Metrics Not Appearing

1. Verify /metrics endpoint is accessible: `curl http://localhost:8000/metrics`
2. Check Prometheus scrape config
3. Verify MetricsMiddleware is registered in app_setup.py
4. Check Prometheus logs for scrape errors

### High Memory Usage

1. Reduce Sentry trace sampling rate (lower than 10%)
2. Check for metric cardinality explosion (too many label combinations)
3. Monitor Prometheus scrape frequency

## Performance Impact

- **Sentry**: Minimal overhead (~1-2ms per request with 10% sampling)
- **Prometheus metrics**: < 1ms per request
- **Total overhead**: < 3ms per request in production

## Security Considerations

1. **Metrics endpoint**: Restrict access via firewall/network rules
2. **Sensitive data**: Automatically filtered before sending to Sentry
3. **Sentry DSN**: Keep secret, don't commit to git
4. **User data**: Never log passwords, tokens, or PII

## Next Steps

After deployment:
1. Set up Sentry project and obtain DSN
2. Configure Prometheus scraping
3. Create Grafana dashboards
4. Set up alerting rules
5. Monitor for 1 week and tune sampling/alerts
6. Document any custom metrics added
