# Performance Regression Tests

This directory contains performance regression tests for the Alloy backend using pytest-benchmark.

## Overview

Performance tests ensure that critical operations maintain acceptable performance thresholds and detect performance regressions before they reach production.

## Test Categories

### Program Creation Tests (`test_program_creation.py`)
- `test_program_creation_8_weeks`: Creating an 8-week program with 4 days/week
- `test_program_creation_12_weeks`: Creating a 12-week program with 5 days/week
- `test_get_single_program`: Retrieving a single program with all relationships
- `test_list_user_programs`: Listing all programs for a user
- `test_list_programs_with_active_filter`: Listing programs with active filter
- `test_get_microcycle_sessions`: Retrieving all sessions for a microcycle
- `test_get_session_with_exercises`: Retrieving a session with exercises loaded

### Session Generation Tests (`test_session_generation.py`)
- `test_generate_single_session`: Generating content for a single session
- `test_generate_upper_body_session`: Generating an upper body session
- `test_generate_lower_body_session`: Generating a lower body session
- `test_generate_recovery_session`: Generating a recovery session
- `test_load_movements_by_pattern`: Loading movements grouped by pattern
- `test_query_movements_by_ids`: Querying movements by IDs
- `test_time_estimation`: Session duration estimation

### Movement Query Tests (`test_movement_queries.py`)
- `test_get_single_movement`: Retrieving a single movement by ID
- `test_list_active_movements`: Listing all active movements
- `test_list_movements_with_pattern_filter`: Listing movements with pattern filter
- `test_list_compound_movements`: Listing compound movements
- `test_list_movements_by_skill_level`: Listing movements by skill level
- `test_query_by_multiple_patterns`: Querying movements by multiple patterns
- `test_query_with_multiple_filters`: Querying movements with multiple filters
- `test_query_by_primary_muscle`: Querying movements by primary muscle
- `test_query_by_primary_region`: Querying movements by primary region
- `test_repository_get`: Repository get method
- `test_repository_list_with_filter`: Repository list method with filters
- `test_repository_list_by_ids`: Repository list_by_ids method
- `test_search_by_name`: Searching movements by name
- `test_search_by_pattern_and_cns_load`: Searching by pattern and CNS load
- `test_count_by_pattern`: Counting movements by pattern
- `test_paginated_list_first_page`: Paginated listing (first page)
- `test_paginated_list_second_page`: Paginated listing (second page)
- `test_total_count_query`: Counting total movements

## Performance Baselines

Baseline performance metrics are stored in `../performance_data/performance_baselines.json`. These are the target performance values:

| Benchmark | Median (ms) | Mean (ms) | Min (ms) | Max (ms) |
|-----------|-------------|------------|----------|----------|
| program_creation | 350.0 | 400.0 | 200.0 | 800.0 |
| session_generation | 2000.0 | 2500.0 | 1000.0 | 5000.0 |
| movement_query_single | 30.0 | 35.0 | 10.0 | 100.0 |
| movement_query_list | 50.0 | 60.0 | 20.0 | 150.0 |
| program_list_query | 40.0 | 50.0 | 15.0 | 120.0 |
| session_list_query | 60.0 | 75.0 | 25.0 | 200.0 |

## Regression Threshold

Tests will fail if performance degrades by more than **10%** from the baseline.

## Running Tests Locally

### Install Dependencies

```bash
pip install pytest-benchmark
```

### Run All Performance Tests

```bash
pytest tests/performance/ --benchmark-only
```

### Run Specific Test Category

```bash
# Program creation tests only
pytest tests/performance/test_program_creation.py --benchmark-only

# Session generation tests only
pytest tests/performance/test_session_generation.py --benchmark-only

# Movement query tests only
pytest tests/performance/test_movement_queries.py --benchmark-only
```

### Run with Verbose Output

```bash
pytest tests/performance/ --benchmark-only -v
```

### Generate Benchmark Report

```bash
# Generate HTML report
pytest tests/performance/ --benchmark-only --benchmark-html=benchmark_report.html

# Generate JSON report
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark_results.json
```

### Update Baselines

To update performance baselines (use after legitimate optimizations):

```bash
pytest tests/performance/ --benchmark-only --benchmark-update-baselines
```

Or commit with message containing `[update-baselines]` to trigger automatic baseline update in CI.

### Run with Detailed Statistics

```bash
pytest tests/performance/ --benchmark-only --benchmark-histogram
```

## GitHub Actions Integration

Performance tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`
- Daily schedule at 2 AM UTC
- Manual workflow dispatch

### CI Behavior

1. **On Pull Requests**: Tests run and results are commented on the PR. If regressions are detected, the comment will highlight which benchmarks failed.

2. **On Push/Schedule**: Tests run and baselines are automatically updated if the commit message contains `[update-baselines]`.

3. **Artifacts**: Benchmark results are uploaded as artifacts for 30 days.

## Interpreting Results

### Passing Test

```
tests/performance/test_program_creation.py::TestProgramCreationBenchmarks::test_program_creation_8_weeks PASSED
------------------------------------------------------------
Benchmark (median): 340.50 ms
Baseline (median): 350.00 ms
Status: PASS (-2.7% improvement)
```

### Failing Test (Regression)

```
tests/performance/test_program_creation.py::TestProgramCreationBenchmarks::test_program_creation_8_weeks FAILED
------------------------------------------------------------
Benchmark (median): 450.00 ms
Baseline (median): 350.00 ms
Status: REGRESSION (+28.6% degradation)
Error: Program creation performance degraded by 28.6% (baseline: 350.0ms, current: 450.0ms)
```

## Troubleshooting

### Tests Fail Intermittently

Performance tests can be sensitive to system load. Run tests multiple times to confirm a genuine regression:

```bash
for i in {1..3}; do echo "Run $i:"; pytest tests/performance/ --benchmark-only --tb=no; done
```

### Baselines Too Aggressive

If baselines are consistently failing due to environment differences, update them:

```bash
pytest tests/performance/ --benchmark-only --benchmark-update-baselines
git add tests/performance_data/performance_baselines.json
git commit -m "Update performance baselines for environment"
```

### Debug Slow Tests

Add detailed logging to understand what's slow:

```python
# Add to test function
import time
start = time.time()
# ... your code ...
elapsed = (time.time() - start) * 1000
print(f"Operation took {elapsed:.2f}ms")
```

## Performance Optimization Tips

### Common Bottlenecks

1. **N+1 Queries**: Use `selectinload()` or `joinedload()` for eager loading relationships
2. **Missing Indexes**: Add database indexes on frequently queried columns
3. **Inefficient Filters**: Use indexed columns in WHERE clauses
4. **Large Result Sets**: Use pagination or limit results

### Optimization Workflow

1. Run performance tests to identify slow operations
2. Profile the operation using Python profiler
3. Implement optimization
4. Re-run tests to verify improvement
5. Update baselines with new improved values

## Adding New Benchmarks

To add a new performance benchmark:

1. Create a new test method in the appropriate file
2. Add the `@pytest.mark.benchmark` decorator
3. Use the `benchmark` fixture to measure your operation
4. Add a baseline entry to `PerformanceBaseline._load_baselines()` in `conftest.py`

Example:

```python
@pytest.mark.benchmark(
    group="my_group",
    min_rounds=10,
    max_time=30,
    timer="perf_counter",
)
async def test_my_new_benchmark(self, benchmark, async_db_session):
    async def _my_operation():
        # Your code here
        return result

    result = benchmark(_my_operation)

    # Check regression
    stats = benchmark.stats
    has_regression, baseline, degradation = performance_baseline.check_regression(
        "my_new_benchmark", stats["median"]
    )

    if has_regression:
        pytest.fail(f"Performance degraded by {degradation:.1f}%")
```

## Continuous Improvement

Performance is an ongoing concern. Regularly:

1. Monitor CI results for trends
2. Profile slow operations
3. Optimize bottlenecks
4. Update baselines after improvements
5. Review and remove obsolete tests

## Resources

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [Python profiling tools](https://docs.python.org/3/library/profile.html)
- [SQLAlchemy performance tips](https://docs.sqlalchemy.org/en/20/core/performance.html)
