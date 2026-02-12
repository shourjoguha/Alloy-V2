"""
Performance benchmarks for session generation operations.

Tests the performance of:
- Session content generation via SessionGeneratorService
- Exercise optimization and selection
- RPE suggestion calculations
"""
import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.session_generator import session_generator
from app.services.program import program_service
from app.models import Program, Microcycle, Session, SessionExercise
from app.models.enums import Goal, SplitTemplate, ProgressionStyle, SessionType
from app.schemas.program import ProgramCreate, GoalWeight, DisciplineWeight
from tests.performance.conftest import performance_baseline


class TestSessionGenerationBenchmarks:
    """Benchmarks for session content generation operations."""

    @pytest.mark.benchmark(
        group="session_generation",
        min_rounds=5,
        max_time=60,
        timer="perf_counter",
        disable_gc=False,
        warmup=False,
    )
    async def test_generate_single_session(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark generating content for a single session."""

        # Create a program first
        request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=8,
            split_template=SplitTemplate.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
        program = await program_service.create_program(
            async_db_session, perf_test_user.id, request
        )

        # Get a pending session
        result = await async_db_session.execute(
            select(Session)
            .join(Microcycle)
            .where(Microcycle.program_id == program.id)
            .where(Session.generation_status == "pending")
            .limit(1)
        )
        session = result.scalar_one()

        # Load related objects
        result = await async_db_session.execute(
            select(Program).where(Program.id == program.id)
        )
        program = result.scalar_one()

        result = await async_db_session.execute(
            select(Microcycle).where(Microcycle.id == session.microcycle_id)
        )
        microcycle = result.scalar_one()

        async def _generate_session():
            return await session_generator.generate_session_exercises(
                db=async_db_session,
                session=session,
                program=program,
                microcycle=microcycle,
            )

        content = benchmark(_generate_session)

        # Verify content was generated
        assert content is not None
        assert "main" in content or "warmup" in content

        # Check regression against baseline
        stats = benchmark.stats
        has_regression, baseline, degradation = performance_baseline.check_regression(
            "session_generation", stats["median"]
        )

        if has_regression:
            pytest.fail(
                f"Session generation performance degraded by {degradation:.1f}% "
                f"(baseline: {baseline:.1f}ms, current: {stats['median']:.1f}ms)"
            )

    @pytest.mark.benchmark(
        group="session_generation",
        min_rounds=3,
        max_time=120,
        timer="perf_counter",
    )
    async def test_generate_upper_body_session(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark generating an upper body session (more complex movement selection)."""

        # Create a program
        request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=6),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=4),
                GoalWeight(goal=Goal.ENDURANCE, weight=0),
            ],
            duration_weeks=8,
            split_template=SplitTemplate.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
        program = await program_service.create_program(
            async_db_session, perf_test_user.id, request
        )

        # Get an upper body session
        result = await async_db_session.execute(
            select(Session)
            .join(Microcycle)
            .where(Microcycle.program_id == program.id)
            .where(Session.session_type == SessionType.UPPER)
            .where(Session.generation_status == "pending")
            .limit(1)
        )
        session = result.scalar_one()

        # Load related objects
        result = await async_db_session.execute(
            select(Program).where(Program.id == program.id)
        )
        program = result.scalar_one()

        result = await async_db_session.execute(
            select(Microcycle).where(Microcycle.id == session.microcycle_id)
        )
        microcycle = result.scalar_one()

        async def _generate_session():
            return await session_generator.generate_session_exercises(
                db=async_db_session,
                session=session,
                program=program,
                microcycle=microcycle,
            )

        content = benchmark(_generate_session)

        # Verify content
        assert content is not None

    @pytest.mark.benchmark(
        group="session_generation",
        min_rounds=3,
        max_time=120,
        timer="perf_counter",
    )
    async def test_generate_lower_body_session(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark generating a lower body session."""

        # Create a program
        request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=6),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=4),
                GoalWeight(goal=Goal.ENDURANCE, weight=0),
            ],
            duration_weeks=8,
            split_template=SplitTemplate.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
        program = await program_service.create_program(
            async_db_session, perf_test_user.id, request
        )

        # Get a lower body session
        result = await async_db_session.execute(
            select(Session)
            .join(Microcycle)
            .where(Microcycle.program_id == program.id)
            .where(Session.session_type == SessionType.LOWER)
            .where(Session.generation_status == "pending")
            .limit(1)
        )
        session = result.scalar_one()

        # Load related objects
        result = await async_db_session.execute(
            select(Program).where(Program.id == program.id)
        )
        program = result.scalar_one()

        result = await async_db_session.execute(
            select(Microcycle).where(Microcycle.id == session.microcycle_id)
        )
        microcycle = result.scalar_one()

        async def _generate_session():
            return await session_generator.generate_session_exercises(
                db=async_db_session,
                session=session,
                program=program,
                microcycle=microcycle,
            )

        content = benchmark(_generate_session)

        # Verify content
        assert content is not None

    @pytest.mark.benchmark(
        group="session_generation",
        min_rounds=5,
        max_time=60,
        timer="perf_counter",
    )
    async def test_generate_recovery_session(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark generating a recovery session (should be fast)."""

        # Create a program
        request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=8,
            split_template=SplitTemplate.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
        program = await program_service.create_program(
            async_db_session, perf_test_user.id, request
        )

        # Get a recovery session
        result = await async_db_session.execute(
            select(Session)
            .join(Microcycle)
            .where(Microcycle.program_id == program.id)
            .where(Session.session_type == SessionType.RECOVERY)
            .where(Session.generation_status == "pending")
            .limit(1)
        )
        session = result.scalar_one()

        # Load related objects
        result = await async_db_session.execute(
            select(Program).where(Program.id == program.id)
        )
        program = result.scalar_one()

        result = await async_db_session.execute(
            select(Microcycle).where(Microcycle.id == session.microcycle_id)
        )
        microcycle = result.scalar_one()

        async def _generate_session():
            return await session_generator.generate_session_exercises(
                db=async_db_session,
                session=session,
                program=program,
                microcycle=microcycle,
            )

        content = benchmark(_generate_session)

        # Verify content
        assert content is not None
        # Recovery sessions should be fast
        assert benchmark.stats["median"] < 100


class TestExerciseGenerationBenchmarks:
    """Benchmarks for specific exercise generation operations."""

    @pytest.mark.benchmark(
        group="exercise_generation",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_load_movements_by_pattern(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark loading movements grouped by pattern."""

        async def _load_movements():
            # Simulate the pattern loading logic from session generator
            from app.models.movement import Movement
            from app.models.enums import MovementPattern

            movements_by_pattern = {}
            for pattern in MovementPattern:
                result = await async_db_session.execute(
                    select(Movement)
                    .where(Movement.pattern == pattern.value)
                    .where(Movement.is_active.is_(True))
                )
                movements_by_pattern[pattern.value] = list(result.scalars().all())
            return movements_by_pattern

        movements_by_pattern = benchmark(_load_movements)

        # Verify loading
        assert len(movements_by_pattern) > 0
        # At least some patterns should have movements
        total = sum(len(m) for m in movements_by_pattern.values())
        assert total > 0

    @pytest.mark.benchmark(
        group="exercise_generation",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_query_movements_by_ids(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark querying movements by IDs (common operation)."""

        # Get some movement IDs
        movement_ids = [m.id for m in perf_test_movements[:10]]

        async def _query_by_ids():
            from app.models.movement import Movement

            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.id.in_(movement_ids))
                .options(selectinload(Movement.movement_disciplines))
                .options(selectinload(Movement.movement_equipment))
            )
            return list(result.scalars().all())

        movements = benchmark(_query_by_ids)

        # Verify retrieval
        assert len(movements) == 10

        # Check regression against baseline
        stats = benchmark.stats
        has_regression, baseline, degradation = performance_baseline.check_regression(
            "movement_query_list", stats["median"]
        )

        if has_regression:
            pytest.fail(
                f"Movement list query performance degraded by {degradation:.1f}% "
                f"(baseline: {baseline:.1f}ms, current: {stats['median']:.1f}ms)"
            )


class TestSessionOptimizationBenchmarks:
    """Benchmarks for session optimization operations."""

    @pytest.mark.benchmark(
        group="session_optimization",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_time_estimation(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark session duration estimation."""

        # Create a program and session with exercises
        request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=5),
                GoalWeight(goal=Goal.ENDURANCE, weight=0),
            ],
            duration_weeks=8,
            split_template=SplitTemplate.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
        program = await program_service.create_program(
            async_db_session, perf_test_user.id, request
        )

        # Get a session
        result = await async_db_session.execute(
            select(Session)
            .join(Microcycle)
            .where(Microcycle.program_id == program.id)
            .limit(1)
        )
        session = result.scalar_one()

        from app.services.time_estimation import time_estimation_service

        async def _estimate_duration():
            return time_estimation_service.calculate_session_duration(session)

        duration = benchmark(_estimate_duration)

        # Verify estimation
        assert duration is not None
        assert duration.total_minutes > 0
