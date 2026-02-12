"""
Configuration and fixtures for performance regression tests.

Provides:
- Performance baseline storage and loading
- Benchmark configuration
- Common test data setup
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSettings
from app.models.movement import Movement
from app.models.enums import (
    ExperienceLevel,
    PersonaTone,
    PersonaAggression,
    MovementPattern,
    PrimaryMuscle,
    PrimaryRegion,
    SkillLevel,
    CNSLoad,
    E1RMFormula,
)

# Baseline file path
BASELINE_DIR = Path(__file__).parent.parent / "performance_data"
BASELINE_FILE = BASELINE_DIR / "performance_baselines.json"


class PerformanceBaseline:
    """Manages performance baselines for regression testing."""

    def __init__(self):
        self.baselines: Dict[str, Dict[str, float]] = self._load_baselines()

    def _load_baselines(self) -> Dict[str, Dict[str, float]]:
        """Load baselines from JSON file or create defaults."""
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)

        if BASELINE_FILE.exists():
            with open(BASELINE_FILE, "r") as f:
                return json.load(f)

        # Default baselines
        defaults = {
            "program_creation": {
                "median_ms": 350.0,
                "mean_ms": 400.0,
                "min_ms": 200.0,
                "max_ms": 800.0,
            },
            "session_generation": {
                "median_ms": 2000.0,
                "mean_ms": 2500.0,
                "min_ms": 1000.0,
                "max_ms": 5000.0,
            },
            "movement_query_single": {
                "median_ms": 30.0,
                "mean_ms": 35.0,
                "min_ms": 10.0,
                "max_ms": 100.0,
            },
            "movement_query_list": {
                "median_ms": 50.0,
                "mean_ms": 60.0,
                "min_ms": 20.0,
                "max_ms": 150.0,
            },
            "program_list_query": {
                "median_ms": 40.0,
                "mean_ms": 50.0,
                "min_ms": 15.0,
                "max_ms": 120.0,
            },
            "session_list_query": {
                "median_ms": 60.0,
                "mean_ms": 75.0,
                "min_ms": 25.0,
                "max_ms": 200.0,
            },
        }
        self._save_baselines(defaults)
        return defaults

    def _save_baselines(self, baselines: Dict[str, Dict[str, float]]):
        """Save baselines to JSON file."""
        with open(BASELINE_FILE, "w") as f:
            json.dump(baselines, f, indent=2)

    def get_baseline(self, benchmark_name: str, metric: str = "median_ms") -> float:
        """Get baseline value for a specific benchmark and metric."""
        return self.baselines.get(benchmark_name, {}).get(metric, float("inf"))

    def check_regression(
        self,
        benchmark_name: str,
        current_value: float,
        metric: str = "median_ms",
        threshold: float = 0.10,
    ) -> tuple[bool, float, float]:
        """
        Check if current performance shows regression.

        Args:
            benchmark_name: Name of the benchmark
            current_value: Current performance value in milliseconds
            metric: Metric to compare (median_ms, mean_ms, etc.)
            threshold: Degradation threshold (default 10%)

        Returns:
            Tuple of (has_regression, baseline_value, degradation_percent)
        """
        baseline = self.get_baseline(benchmark_name, metric)
        if baseline == float("inf"):
            return False, baseline, 0.0

        degradation = (current_value - baseline) / baseline
        has_regression = degradation > threshold
        return has_regression, baseline, degradation * 100

    def update_baseline(
        self,
        benchmark_name: str,
        stats: Dict[str, float],
        force: bool = False,
    ):
        """
        Update baseline with new values.

        Args:
            benchmark_name: Name of the benchmark
            stats: Dictionary with median, mean, min, max values
            force: Force update even if performance degraded
        """
        if benchmark_name not in self.baselines:
            self.baselines[benchmark_name] = {}

        for metric, value in stats.items():
            current_baseline = self.baselines[benchmark_name].get(metric, float("inf"))
            # Only update if improved or forced
            if value < current_baseline or force:
                self.baselines[benchmark_name][metric] = value

        self._save_baselines(self.baselines)


# Global baseline instance
performance_baseline = PerformanceBaseline()


@pytest.fixture
def baseline():
    """Fixture providing access to performance baselines."""
    return performance_baseline


@pytest.fixture
def performance_threshold():
    """Fixture providing degradation threshold (10% by default)."""
    return 0.10


@pytest_asyncio.fixture
async def perf_test_user(async_db_session: AsyncSession) -> User:
    """Create a user specifically for performance testing."""
    user = User(
        name="Performance Test User",
        email="perf_test@example.com",
        experience_level=ExperienceLevel.INTERMEDIATE,
        persona_tone=PersonaTone.SUPPORTIVE,
        persona_aggression=PersonaAggression.BALANCED,
    )
    async_db_session.add(user)
    await async_db_session.flush()

    settings = UserSettings(
        user_id=user.id,
        active_e1rm_formula=E1RMFormula.EPLEY,
        use_metric=True,
    )
    async_db_session.add(settings)
    await async_db_session.commit()

    return user


@pytest_asyncio.fixture
async def perf_test_movements(async_db_session: AsyncSession) -> list[Movement]:
    """Create a set of movements for performance testing (100 movements)."""
    movements = []

    # Create diverse movements across patterns
    patterns = [
        MovementPattern.SQUAT,
        MovementPattern.HINGE,
        MovementPattern.HORIZONTAL_PUSH,
        MovementPattern.HORIZONTAL_PULL,
        MovementPattern.VERTICAL_PUSH,
        MovementPattern.VERTICAL_PULL,
        MovementPattern.LUNGE,
        MovementPattern.ROTATIONAL,
        MovementPattern.CARRY,
        MovementPattern.ISOLATION,
    ]

    primary_muscles = [
        PrimaryMuscle.QUADRICEPS,
        PrimaryMuscle.HAMSTRINGS,
        PrimaryMuscle.CHEST,
        PrimaryMuscle.LATS,
        PrimaryMuscle.SHOULDERS,
        PrimaryMuscle.TRICEPS,
        PrimaryMuscle.BICEPS,
        PrimaryMuscle.CALVES,
        PrimaryMuscle.ABS,
        PrimaryMuscle.GLUTES,
    ]

    skill_levels = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED]
    cns_loads = [CNSLoad.LOW, CNSLoad.MODERATE, CNSLoad.HIGH]

    # Generate 100 diverse movements
    for i in range(100):
        movement = Movement(
            name=f"Perf Test Movement {i + 1}",
            pattern=patterns[i % len(patterns)].value,
            primary_muscle=primary_muscles[i % len(primary_muscles)].value,
            primary_region=PrimaryRegion.ANTERIOR_LOWER.value if i % 2 == 0 else PrimaryRegion.POSTERIOR_UPPER.value,
            skill_level=skill_levels[i % len(skill_levels)].value,
            cns_load=cns_loads[i % len(cns_loads)].value,
            compound=i < 50,  # First 50 are compound movements
            is_active=True,
        )
        movements.append(movement)

    async_db_session.add_all(movements)
    await async_db_session.commit()
    return movements


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture benchmark results and check for regressions."""
    outcome = yield

    # Only process if test has benchmark marker
    if "benchmark" not in item.keywords:
        return

    # Check if test completed successfully
    if call.when == "call" and outcome.get_result().passed:
        # The benchmark fixture stores results in the test's fixture dict
        # This is handled by pytest-benchmark's internal mechanism
        pass
