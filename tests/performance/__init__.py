"""
Performance regression tests for Alloy backend.

This package contains benchmarks for critical API endpoints and service operations.
Tests use pytest-benchmark to measure performance over time and detect regressions.

Test Categories:
- Program Creation: Benchmark program creation API endpoint
- Session Generation: Benchmark session generation service
- Movement Queries: Benchmark movement query operations

Performance Baselines:
- Program creation: < 500ms (p95)
- Session generation: < 3000ms (p95)
- Movement queries: < 100ms (p95)

Degradation Threshold: 10%
If performance degrades beyond 10% from baseline, tests will fail.
"""
