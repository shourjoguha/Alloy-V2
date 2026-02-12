"""
Performance benchmarks for program creation operations.

Tests the performance of:
- Program creation via ProgramService
- Program retrieval via repository
- Program listing queries
- Microcycle and session generation
"""
import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.program import program_service
from app.models import Program, Microcycle, Session
from app.models.enums import Goal, SplitTemplate, ProgressionStyle
from app.schemas.program import ProgramCreate, GoalWeight, DisciplineWeight
from tests.performance.conftest import performance_baseline


class TestProgramCreationBenchmarks:
    """Benchmarks for program creation and retrieval operations."""

    @pytest.mark.benchmark(
        group="program_creation",
        min_rounds=5,
        max_time=60,
        timer="perf_counter",
        disable_gc=False,
        warmup=False,
    )
    async def test_program_creation_8_weeks(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark creating an 8-week program with 4 days per week."""

        async def _create_program():
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
                disciplines=[
                    DisciplineWeight(discipline="powerlifting", weight=5),
                    DisciplineWeight(discipline="bodybuilding", weight=5),
                ],
            )
            return await program_service.create_program(
                async_db_session, perf_test_user.id, request
            )

        program = benchmark(_create_program)

        # Verify program was created
        assert program.id is not None
        assert program.duration_weeks == 8
        assert program.days_per_week == 4

        # Check regression against baseline
        stats = benchmark.stats
        has_regression, baseline, degradation = performance_baseline.check_regression(
            "program_creation", stats["median"]
        )

        if has_regression:
            pytest.fail(
                f"Program creation performance degraded by {degradation:.1f}% "
                f"(baseline: {baseline:.1f}ms, current: {stats['median']:.1f}ms)"
            )

    @pytest.mark.benchmark(
        group="program_creation",
        min_rounds=5,
        max_time=60,
        timer="perf_counter",
    )
    async def test_program_creation_12_weeks(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark creating a 12-week program with 5 days per week."""

        async def _create_program():
            request = ProgramCreate(
                goals=[
                    GoalWeight(goal=Goal.STRENGTH, weight=6),
                    GoalWeight(goal=Goal.EXPLOSIVENESS, weight=4),
                    GoalWeight(goal=Goal.SPEED, weight=0),
                ],
                duration_weeks=12,
                split_template=SplitTemplate.PUSH_PULL_LEGS,
                days_per_week=5,
                progression_style=ProgressionStyle.LINEAR,
                disciplines=[
                    DisciplineWeight(discipline="crossfit", weight=5),
                    DisciplineWeight(discipline="powerlifting", weight=5),
                ],
            )
            return await program_service.create_program(
                async_db_session, perf_test_user.id, request
            )

        program = benchmark(_create_program)

        # Verify program was created
        assert program.id is not None
        assert program.duration_weeks == 12
        assert program.days_per_week == 5

        # Load microcycles to verify full structure
        await async_db_session.refresh(program, ["microcycles"])
        assert len(program.microcycles) > 0


class TestProgramRetrievalBenchmarks:
    """Benchmarks for program retrieval and listing operations."""

    @pytest.mark.benchmark(
        group="program_retrieval",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_get_single_program(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark retrieving a single program with all relationships."""

        # Create a test program first
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

        async def _get_program():
            result = await async_db_session.execute(
                select(Program)
                .options(
                    selectinload(Program.microcycles).selectinload(Microcycle.sessions)
                )
                .where(Program.id == program.id)
            )
            return result.scalar_one()

        retrieved_program = benchmark(_get_program)

        # Verify retrieval
        assert retrieved_program.id == program.id
        assert len(retrieved_program.microcycles) > 0

    @pytest.mark.benchmark(
        group="program_retrieval",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_list_user_programs(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark listing all programs for a user."""

        # Create multiple programs
        for i in range(5):
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
            await program_service.create_program(
                async_db_session, perf_test_user.id, request
            )

        async def _list_programs():
            result = await async_db_session.execute(
                select(Program)
                .where(Program.user_id == perf_test_user.id)
                .order_by(Program.created_at.desc())
            )
            return list(result.scalars().all())

        programs = benchmark(_list_programs)

        # Verify listing
        assert len(programs) >= 5

        # Check regression against baseline
        stats = benchmark.stats
        has_regression, baseline, degradation = performance_baseline.check_regression(
            "program_list_query", stats["median"]
        )

        if has_regression:
            pytest.fail(
                f"Program list query performance degraded by {degradation:.1f}% "
                f"(baseline: {baseline:.1f}ms, current: {stats['median']:.1f}ms)"
            )

    @pytest.mark.benchmark(
        group="program_retrieval",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_list_programs_with_active_filter(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark listing programs with active-only filter."""

        # Create programs with varying active status
        for i in range(5):
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
            # Make only the last one active
            if i == 4:
                program.is_active = True
                await async_db_session.commit()

        async def _list_active_programs():
            result = await async_db_session.execute(
                select(Program)
                .where(Program.user_id == perf_test_user.id)
                .where(Program.is_active.is_(True))
                .order_by(Program.created_at.desc())
            )
            return list(result.scalars().all())

        active_programs = benchmark(_list_active_programs)

        # Verify filtering
        assert len(active_programs) == 1


class TestSessionRetrievalBenchmarks:
    """Benchmarks for session retrieval operations."""

    @pytest.mark.benchmark(
        group="session_retrieval",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_get_microcycle_sessions(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark retrieving all sessions for a microcycle."""

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

        # Get active microcycle
        result = await async_db_session.execute(
            select(Microcycle)
            .where(Microcycle.program_id == program.id)
            .where(Microcycle.status == "active")
        )
        microcycle = result.scalar_one()

        async def _get_sessions():
            result = await async_db_session.execute(
                select(Session)
                .where(Session.microcycle_id == microcycle.id)
                .order_by(Session.day_number)
            )
            return list(result.scalars().all())

        sessions = benchmark(_get_sessions)

        # Verify retrieval
        assert len(sessions) > 0

        # Check regression against baseline
        stats = benchmark.stats
        has_regression, baseline, degradation = performance_baseline.check_regression(
            "session_list_query", stats["median"]
        )

        if has_regression:
            pytest.fail(
                f"Session list query performance degraded by {degradation:.1f}% "
                f"(baseline: {baseline:.1f}ms, current: {stats['median']:.1f}ms)"
            )

    @pytest.mark.benchmark(
        group="session_retrieval",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_get_session_with_exercises(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_user,
        perf_test_movements,
    ):
        """Benchmark retrieving a session with exercises loaded."""

        # Create a program
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

        # Get first session
        result = await async_db_session.execute(
            select(Session)
            .join(Microcycle)
            .where(Microcycle.program_id == program.id)
            .limit(1)
        )
        session = result.scalar_one()

        async def _get_session_with_exercises():
            result = await async_db_session.execute(
                select(Session)
                .where(Session.id == session.id)
                .options(selectinload(Session.exercises))
            )
            return result.scalar_one()

        retrieved_session = benchmark(_get_session_with_exercises)

        # Verify retrieval
        assert retrieved_session.id == session.id
