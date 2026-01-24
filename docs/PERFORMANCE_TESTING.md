# Performance Testing Guide

## Overview

ShowMeGains backend performance tests validate system behavior under load using Locust, a Python-based load testing framework.

## Setup

### Install Locust

```bash
pip install locust
# Or add to requirements.txt and install:
# pip install -r requirements.txt
```

### Ensure App is Running

```bash
# In one terminal, start Ollama (required for adaptation endpoint)
ollama serve

# In another terminal, start the FastAPI app
uvicorn app.main:app --reload --port 8000
```

## Running Performance Tests

### Basic Load Test

Start the Locust Web UI with default settings:

```bash
locust -f tests/performance_test_locust.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser and configure:
- Number of users: 10-50
- Spawn rate: 2-10 users/second
- Duration: 5-10 minutes

### Headless Testing (Scripted)

Run with specific parameters without the Web UI:

```bash
# Light load test: 10 users over 5 minutes
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=10 --spawn-rate=2 --run-time=5m --headless

# Medium load test: 50 users over 10 minutes
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=50 --spawn-rate=5 --run-time=10m --headless

# Stress test: 100 users over 15 minutes
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=100 --spawn-rate=10 --run-time=15m --headless
```

### Test Scenarios

#### 1. Load Test (Normal Usage)

**Goal**: Validate performance with realistic concurrent user load

```bash
# 20 concurrent users, realistic think time
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=20 --spawn-rate=2 --run-time=10m --headless
```

**Expected Metrics**:
- p95 response time < 500ms (plan endpoint)
- p95 response time < 2000ms (adapt endpoint, includes LLM)
- Throughput: 10-20 requests/second
- Error rate: 0%

#### 2. Stress Test (Heavy Usage)

**Goal**: Find breaking points and system behavior under overload

```bash
# 100 concurrent users, aggressive think time
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=100 --spawn-rate=10 --run-time=15m --headless
```

**Expected Metrics**:
- p95 response time < 1000ms (degraded but acceptable)
- Throughput: 20-40 requests/second
- Error rate: <5% (some LLM timeouts acceptable)

#### 3. Spike Test (Sudden Load)

**Goal**: Validate recovery from traffic spikes

```bash
# Start with 10 users, jump to 100 every 2 minutes
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=100 --spawn-rate=50 --run-time=10m --headless
```

**Expected Metrics**:
- Recovery time: <30 seconds after spike
- No cascading failures
- Database connections remain stable

#### 4. Endurance Test (Long Duration)

**Goal**: Detect memory leaks and connection pooling issues

```bash
# Moderate load over extended period
locust -f tests/performance_test_locust.py \
    --host=http://localhost:8000 \
    --users=30 --spawn-rate=3 --run-time=30m --headless
```

**Expected Metrics**:
- Memory usage stable (no growth > 5% per 5 minutes)
- Database connections stable (no leaks)
- Response times consistent (no degradation)

## Interpreting Results

### Key Metrics

- **Response Time (p50/p95/p99)**: Latency percentiles
  - p50: Median (50% of requests faster)
  - p95: 95th percentile (acceptable for most use cases)
  - p99: 99th percentile (worst-case latency)

- **Throughput**: Requests per second
  - Indicates endpoint capacity

- **Error Rate**: Failed requests as percentage
  - Timeouts (LLM service delays)
  - 4xx/5xx HTTP errors

- **Users**: Concurrent active users

- **Requests/sec**: Current request rate

### Success Criteria

✅ **All Metrics OK**:
- p95 response time < 500ms (plan), < 2000ms (adapt)
- Error rate < 1%
- Throughput > 10 req/sec at 50 users

⚠️ **Acceptable with Caveats**:
- p99 response time elevated (> 5000ms)
  - Normal for LLM-dependent endpoints
  - Acceptable if p95 within limits

❌ **Red Flags**:
- Increasing memory usage over time
- Database connection errors
- Cascading failures under spike
- p95 > 2000ms for plan endpoint (database issue)

## Performance Analysis

### Database Bottlenecks

If `get_daily_plan` (fast endpoint) exceeds 200ms p95:

1. Check database indexes on Program, Microcycle, Session
2. Look for N+1 queries in SQLAlchemy relationships
3. Add `selectinload()` for eager loading if needed

### LLM Bottlenecks

If `request_adaptation` exceeds 5000ms p95:

1. Normal - LLM inference takes 2-10 seconds
2. Set LLM timeout in config (currently 120s)
3. Consider caching frequent adaptation patterns

### Concurrency Issues

If error rate spikes with increasing users:

1. Check SQLite concurrent write limits
  - Consider upgrading to PostgreSQL for production
2. Verify connection pooling in SQLAlchemy settings
3. Check for deadlocks in database logs

## Sample Results

### Baseline (Initial Implementation)

```
ShowMeGains Performance Test - Initial
Users: 20
Duration: 10 minutes

Requests:
├─ GET /days/{date}/plan: 2400 req, 98% OK
│  └─ Response time: p50=120ms, p95=280ms, p99=450ms
├─ POST /days/{date}/adapt: 1800 req, 95% OK
│  └─ Response time: p50=2500ms, p95=4200ms, p99=6800ms (LLM latency)
├─ POST /logs/workout: 1200 req, 100% OK
│  └─ Response time: p50=45ms, p95=95ms, p99=150ms
└─ Other: 600 req, 99% OK

Total Throughput: 268 req/min (~4.5 req/sec)
```

## Documentation Updates

After running tests, document:
1. Date and configuration (users, duration, app version)
2. Key metrics (p50/p95/p99, error rate)
3. Notable findings (bottlenecks, issues)
4. Recommendations for optimization

## Troubleshooting

### Locust Won't Connect

```bash
# Verify app is running
curl http://localhost:8000/docs

# Check if port 8000 is available
lsof -i :8000
```

### High Error Rate

```bash
# Check app logs for errors
# Verify Ollama is running for LLM endpoints
ollama serve

# Monitor database
# Look for: "database is locked" (SQLite concurrency)
```

### Memory Leak Suspected

```bash
# Run with memory monitoring
# macOS: Activity Monitor or top
top -p $(pgrep -f "uvicorn")

# After test, compare memory at start vs end
```

## Next Steps

- Optimize identified bottlenecks
- Run regression tests after changes
- Document performance baselines
- Plan database migration (SQLite → PostgreSQL) for production

