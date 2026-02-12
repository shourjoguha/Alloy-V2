# Load Testing

Automated load testing using Locust for the Alloy API.

## Prerequisites

Install Locust:

```bash
pip install locust
```

## Quick Start

### Web UI Mode (Recommended for Development)

```bash
locust -f tests/load_test/locustfile.py -H http://localhost:8000
```

Open browser to `http://localhost:8089`

### Headless Mode (CI/CD)

```bash
locust -f tests/load_test/locustfile.py -H http://localhost:8000 --headless -u 100 -r 10 -t 5m
```

## Test Scenarios

### AlloyUser (Standard Load)

Simulates normal user behavior:
- Health checks (30%)
- List circuits (50%)
- List movements (100%)
- List programs (70%)
- Get program details (30%)
- Get program stats (20%)

**Recommended:**
- Users: 50-200
- Spawn Rate: 5-20 users/second
- Duration: 10-30 minutes

### StressTestUser (Stress Test)

High-intensity testing:
- Rapid health checks (10x frequency)
- Rapid circuit listing (15x frequency)

**Recommended:**
- Users: 500-1000
- Spawn Rate: 50-100 users/second
- Duration: 5-15 minutes

## CI/CD Integration

### GitHub Actions

```yaml
name: Load Tests

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    services:
      api:
        image: alloy-api:latest
        ports:
          - 8000:8000
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Locust
        run: pip install locust
      
      - name: Run Load Tests
        run: |
          locust -f tests/load_test/locustfile.py \
            -H http://localhost:8000 \
            --headless \
            -u 50 \
            -r 5 \
            -t 10m \
            --csv load_test_results
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: load_test_results_*.csv
```

### GitLab CI

```yaml
load_test:
  stage: test
  image: python:3.11
  services:
    - name: api
      image: alloy-api:latest
  
  script:
    - pip install locust
    - locust -f tests/load_test/locustfile.py \
        -H http://api:8000 \
        --headless \
        -u 50 \
        -r 5 \
        -t 10m \
        --html report.html
  
  artifacts:
    paths:
      - report.html
    when: always
```

## Performance Baselines

| Endpoint | Target P95 | Target P99 | Target RPS |
|----------|------------|------------|------------|
| `GET /health` | < 50ms | < 100ms | > 500 |
| `GET /circuits` | < 100ms | < 200ms | > 200 |
| `GET /settings/movements` | < 150ms | < 300ms | > 100 |
| `GET /programs` | < 200ms | < 400ms | > 50 |
| `POST /auth/login` | < 300ms | < 600ms | > 20 |

## Alerts

### Critical (P0)
- Error rate > 5%
- P95 latency > 2x baseline
- Failures > 10%

### Warning (P1)
- Error rate > 1%
- P95 latency > 1.5x baseline
- Failures > 5%

## Analysis

### View Results

After running tests, analyze:

```bash
# View CSV results
cat load_test_results_stats.csv

# View distribution
cat load_test_results_stats_history.csv

# View failures
cat load_test_results_failures.csv
```

### Generate HTML Report

```bash
locust -f tests/load_test/locustfile.py \
  -H http://localhost:8000 \
  --headless \
  -u 50 \
  -r 5 \
  -t 10m \
  --html report.html

open report.html
```

## Troubleshooting

### Connection Refused
Ensure API is running:
```bash
curl http://localhost:8000/health
```

### High Error Rate
Check logs:
```bash
docker-compose logs api
```

### Slow Response Times
- Check database performance
- Verify cache is working
- Review slow query logs

## Advanced Configuration

### Custom User Email/Password

```bash
LOCUST_USER_EMAIL=user@example.com \
LOCUST_USER_PASSWORD=secure_password \
locust -f tests/load_test/locustfile.py -H http://localhost:8000
```

### Distributed Testing

```bash
# Master
locust -f tests/load_test/locustfile.py -H http://localhost:8000 \
  --master --expect-workers=4

# Worker 1
locust -f tests/load_test/locustfile.py -H http://localhost:8000 \
  --worker --master-host=localhost

# Worker 2, 3, 4...
```

### Custom Test Scenarios

Create new user class:

```python
class CustomUser(AlloyUser):
    """Custom test scenario."""
    
    wait_time = between(2, 8)
    
    @task(5)
    def custom_action(self):
        """Your custom test logic."""
        pass
```

## References

- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://docs.locust.io/en/stable/testing-best-practices.html)
