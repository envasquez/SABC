# Load Testing Documentation

This directory contains load testing scenarios for the SABC application using Locust.

## Prerequisites

```bash
pip install locust
```

Or add to requirements:
```bash
echo "locust==2.29.1" >> requirements-test.txt
```

## Quick Start

### 1. Start the Application

```bash
# Terminal 1: Start SABC application
nix develop -c start-app
```

### 2. Run Load Tests

```bash
# Terminal 2: Start Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### 3. Access Web UI

Open browser to: **http://localhost:8089**

Configure:
- **Number of users**: Start with 10-50
- **Spawn rate**: 1-5 users/second
- **Host**: http://localhost:8000

## Test Scenarios

### BrowsingUser
Simulates anonymous users browsing public pages:
- Homepage (most common)
- Calendar
- Awards/standings
- Health checks

**Usage**: Tests basic read performance and caching

### AuthenticatedUser
Simulates logged-in members:
- Viewing polls
- Profile management
- Calendar and homepage

**Usage**: Tests session management and member-only features

### AdminUser
Simulates admin users performing management tasks:
- Admin dashboard
- Event management
- User management

**Usage**: Tests admin authorization and complex queries

### MixedWorkload
Realistic mix of user types and behaviors

**Usage**: Production-like traffic simulation

## Running Tests from CLI

### Quick Performance Check
```bash
# Run 50 users for 60 seconds
locust -f tests/load/locustfile.py \\
  --host=http://localhost:8000 \\
  --users 50 \\
  --spawn-rate 5 \\
  --run-time 60s \\
  --headless \\
  --html=tests/load/report.html
```

### Stress Test
```bash
# Gradually increase to 200 users
locust -f tests/load/locustfile.py \\
  --host=http://localhost:8000 \\
  --users 200 \\
  --spawn-rate 10 \\
  --run-time 300s \\
  --headless \\
  --csv=tests/load/stress_test
```

### Spike Test
```bash
# Sudden spike of 100 users
locust -f tests/load/locustfile.py \\
  --host=http://localhost:8000 \\
  --users 100 \\
  --spawn-rate 50 \\
  --run-time 120s \\
  --headless
```

## Performance Targets

### Response Times (P95)
- **Homepage**: < 200ms
- **Calendar**: < 300ms
- **Awards**: < 500ms (complex query)
- **Polls**: < 250ms
- **Admin pages**: < 500ms

### Throughput
- **50 concurrent users**: < 1% error rate
- **100 concurrent users**: < 2% error rate
- **200 concurrent users**: < 5% error rate

### Resource Usage
- **Memory**: < 100MB per instance
- **CPU**: < 70% average
- **Database connections**: < 20 active

## Interpreting Results

### Green Flags ✅
- P95 response time < 500ms
- Error rate < 1%
- Consistent throughput
- Stable memory usage

### Yellow Flags ⚠️
- P95 response time 500ms - 1s
- Error rate 1% - 5%
- Increasing response times
- Gradual memory increase

### Red Flags 🔴
- P95 response time > 1s
- Error rate > 5%
- Timeouts or connection errors
- Memory leaks
- Database connection pool exhaustion

## Test Data Requirements

For authenticated user tests, create test accounts:

```sql
-- Create load test member
INSERT INTO anglers (name, email, password_hash, member, phone, is_admin)
VALUES (
  'Load Test User',
  'loadtest@example.com',
  '$2b$12$...',  -- Hash for 'LoadTest123!'
  true,
  '555-0100',
  false
);

-- Create load test admin
INSERT INTO anglers (name, email, password_hash, member, phone, is_admin)
VALUES (
  'Load Test Admin',
  'admin@example.com',
  '$2b$12$...',  -- Hash for 'Admin123!'
  true,
  '555-0101',
  true
);
```

## Distributed Load Testing

For testing with multiple machines:

### Master Node
```bash
locust -f tests/load/locustfile.py \\
  --master \\
  --expect-workers=3
```

### Worker Nodes
```bash
locust -f tests/load/locustfile.py \\
  --worker \\
  --master-host=<master-ip>
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Load Tests
  run: |
    pip install locust
    locust -f tests/load/locustfile.py \\
      --host=${{ secrets.STAGING_URL }} \\
      --users 50 \\
      --spawn-rate 5 \\
      --run-time 60s \\
      --headless \\
      --html=load-test-report.html \\
      --only-summary

- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: load-test-report
    path: load-test-report.html
```

## Troubleshooting

### High Error Rates
- Check application logs
- Verify database connections
- Check for rate limiting
- Ensure test data exists

### Slow Response Times
- Profile with Locust web UI
- Check database query performance
- Review caching strategy
- Check for N+1 queries

### Connection Errors
- Verify application is running
- Check firewall rules
- Increase connection limits
- Check for port conflicts

## Best Practices

1. **Start Small**: Begin with 10 users, gradually increase
2. **Monitor Resources**: Watch CPU, memory, database connections
3. **Use Realistic Data**: Test with production-like data volumes
4. **Test Edge Cases**: Include error scenarios in tests
5. **Automate**: Run load tests before deployments
6. **Document Baselines**: Record performance metrics over time
7. **Test Regularly**: Weekly or before major releases

## Resources

- **Locust Documentation**: https://docs.locust.io/
- **Performance Testing Guide**: https://www.nginx.com/blog/load-testing-best-practices/
- **SABC Testing Docs**: ../TESTING.md
