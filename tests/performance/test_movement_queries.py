"""
Performance benchmarks for movement query operations.

Tests the performance of:
- Single movement retrieval
- Movement listing with filters
- Movement pattern queries
- Movement equipment queries
- Movement discipline queries
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload

from app.models.movement import Movement
from app.models.enums import MovementPattern, PrimaryMuscle, PrimaryRegion, SkillLevel, CNSLoad
from app.repositories.movement_repository import MovementRepository
from app.schemas.pagination import PaginationParams
from tests.performance.conftest import performance_baseline


class TestMovementRetrievalBenchmarks:
    """Benchmarks for movement retrieval operations."""

    @pytest.mark.benchmark(
        group="movement_retrieval",
        min_rounds=20,
        max_time=30,
        timer="perf_counter",
    )
    async def test_get_single_movement(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark retrieving a single movement by ID with all relationships."""

        movement_id = perf_test_movements[0].id

        async def _get_movement():
            result = await async_db_session.execute(
                select(Movement)
                .options(selectinload(Movement.movement_disciplines))
                .options(selectinload(Movement.movement_equipment))
                .options(selectinload(Movement.movement_tags))
                .where(Movement.id == movement_id)
            )
            return result.scalar_one()

        movement = benchmark(_get_movement)

        # Verify retrieval
        assert movement.id == movement_id

        # Check regression against baseline
        stats = benchmark.stats
        has_regression, baseline, degradation = performance_baseline.check_regression(
            "movement_query_single", stats["median"]
        )

        if has_regression:
            pytest.fail(
                f"Single movement query performance degraded by {degradation:.1f}% "
                f"(baseline: {baseline:.1f}ms, current: {stats['median']:.1f}ms)"
            )

    @pytest.mark.benchmark(
        group="movement_retrieval",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_list_active_movements(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark listing all active movements."""

        async def _list_movements():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_list_movements)

        # Verify listing
        assert len(movements) > 0
        assert all(m.is_active for m in movements)

    @pytest.mark.benchmark(
        group="movement_retrieval",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_list_movements_with_pattern_filter(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark listing movements with pattern filter."""

        async def _list_by_pattern():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.pattern == MovementPattern.SQUAT.value)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_list_by_pattern)

        # Verify filtering
        assert len(movements) > 0
        assert all(m.pattern == MovementPattern.SQUAT.value for m in movements)

    @pytest.mark.benchmark(
        group="movement_retrieval",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_list_compound_movements(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark listing compound movements."""

        async def _list_compound():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.compound.is_(True))
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_list_compound)

        # Verify filtering
        assert len(movements) > 0
        assert all(m.compound for m in movements)

    @pytest.mark.benchmark(
        group="movement_retrieval",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_list_movements_by_skill_level(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark listing movements by skill level."""

        async def _list_by_skill():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.skill_level == SkillLevel.INTERMEDIATE.value)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_list_by_skill)

        # Verify filtering
        assert len(movements) > 0
        assert all(m.skill_level == SkillLevel.INTERMEDIATE.value for m in movements)


class TestMovementComplexQueriesBenchmarks:
    """Benchmarks for complex movement query operations."""

    @pytest.mark.benchmark(
        group="movement_complex_queries",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_query_by_multiple_patterns(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark querying movements by multiple patterns (OR condition)."""

        async def _query_patterns():
            result = await async_db_session.execute(
                select(Movement)
                .where(
                    or_(
                        Movement.pattern == MovementPattern.SQUAT.value,
                        Movement.pattern == MovementPattern.HINGE.value,
                        Movement.pattern == MovementPattern.HORIZONTAL_PUSH.value,
                    )
                )
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_query_patterns)

        # Verify query
        assert len(movements) > 0

    @pytest.mark.benchmark(
        group="movement_complex_queries",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_query_with_multiple_filters(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark querying movements with multiple filters."""

        async def _query_filtered():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.compound.is_(True))
                .where(Movement.skill_level == SkillLevel.INTERMEDIATE.value)
                .where(Movement.cns_load == CNSLoad.MODERATE.value)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_query_filtered)

        # Verify filtering
        assert len(movements) > 0
        assert all(
            m.compound
            and m.skill_level == SkillLevel.INTERMEDIATE.value
            and m.cns_load == CNSLoad.MODERATE.value
            for m in movements
        )

    @pytest.mark.benchmark(
        group="movement_complex_queries",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_query_by_primary_muscle(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark querying movements by primary muscle."""

        async def _query_by_muscle():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.primary_muscle == PrimaryMuscle.QUADRICEPS.value)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_query_by_muscle)

        # Verify query
        assert len(movements) > 0
        assert all(m.primary_muscle == PrimaryMuscle.QUADRICEPS.value for m in movements)

    @pytest.mark.benchmark(
        group="movement_complex_queries",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_query_by_primary_region(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark querying movements by primary region."""

        async def _query_by_region():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.primary_region == PrimaryRegion.ANTERIOR_LOWER.value)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_query_by_region)

        # Verify query
        assert len(movements) > 0
        assert all(
            m.primary_region == PrimaryRegion.ANTERIOR_LOWER.value for m in movements
        )


class TestMovementRepositoryBenchmarks:
    """Benchmarks for MovementRepository operations."""

    @pytest.mark.benchmark(
        group="movement_repository",
        min_rounds=20,
        max_time=30,
        timer="perf_counter",
    )
    async def test_repository_get(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark repository get method."""

        repo = MovementRepository(async_db_session)
        movement_id = perf_test_movements[0].id

        async def _repo_get():
            return await repo.get(movement_id)

        movement = benchmark(_repo_get)

        # Verify retrieval
        assert movement.id == movement_id

    @pytest.mark.benchmark(
        group="movement_repository",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_repository_list_with_filter(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark repository list method with filters."""

        repo = MovementRepository(async_db_session)
        pagination = PaginationParams(limit=20, cursor=None, direction="next")

        async def _repo_list():
            return await repo.list(
                filter={"is_active": True, "pattern": MovementPattern.SQUAT.value},
                pagination=pagination,
            )

        result = benchmark(_repo_list)

        # Verify listing
        assert len(result.items) > 0

    @pytest.mark.benchmark(
        group="movement_repository",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_repository_list_by_ids(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark repository list_by_ids method."""

        repo = MovementRepository(async_db_session)
        movement_ids = [m.id for m in perf_test_movements[:10]]

        async def _repo_list_ids():
            return await repo.list_by_ids(movement_ids)

        movements = benchmark(_repo_list_ids)

        # Verify retrieval
        assert len(movements) == 10


class TestMovementSearchBenchmarks:
    """Benchmarks for movement search operations."""

    @pytest.mark.benchmark(
        group="movement_search",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_search_by_name(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark searching movements by name (LIKE query)."""

        async def _search_name():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.name.like("%Test%"))
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_search_name)

        # Verify search
        assert len(movements) > 0
        assert all("Test" in m.name for m in movements)

    @pytest.mark.benchmark(
        group="movement_search",
        min_rounds=15,
        max_time=30,
        timer="perf_counter",
    )
    async def test_search_by_pattern_and_cns_load(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark searching movements by pattern and CNS load."""

        async def _search_combined():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.pattern == MovementPattern.SQUAT.value)
                .where(Movement.cns_load == CNSLoad.HIGH.value)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
            )
            return list(result.scalars().all())

        movements = benchmark(_search_combined)

        # Verify search
        assert len(movements) >= 0  # May be empty, that's okay

    @pytest.mark.benchmark(
        group="movement_search",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_count_by_pattern(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark counting movements by pattern."""

        async def _count_pattern():
            from sqlalchemy import func

            result = await async_db_session.execute(
                select(func.count(Movement.id)).where(
                    Movement.pattern == MovementPattern.SQUAT.value
                )
            )
            return result.scalar()

        count = benchmark(_count_pattern)

        # Verify count
        assert count >= 0


class TestMovementPaginationBenchmarks:
    """Benchmarks for movement pagination operations."""

    @pytest.mark.benchmark(
        group="movement_pagination",
        min_rounds=20,
        max_time=30,
        timer="perf_counter",
    )
    async def test_paginated_list_first_page(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark paginated movement listing (first page)."""

        async def _paginated_list():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
                .limit(20)
            )
            return list(result.scalars().all())

        movements = benchmark(_paginated_list)

        # Verify pagination
        assert len(movements) <= 20

    @pytest.mark.benchmark(
        group="movement_pagination",
        min_rounds=20,
        max_time=30,
        timer="perf_counter",
    )
    async def test_paginated_list_second_page(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark paginated movement listing (second page with offset)."""

        async def _paginated_list_offset():
            result = await async_db_session.execute(
                select(Movement)
                .where(Movement.is_active.is_(True))
                .order_by(Movement.name)
                .limit(20)
                .offset(20)
            )
            return list(result.scalars().all())

        movements = benchmark(_paginated_list_offset)

        # Verify pagination
        assert len(movements) <= 20

    @pytest.mark.benchmark(
        group="movement_pagination",
        min_rounds=10,
        max_time=30,
        timer="perf_counter",
    )
    async def test_total_count_query(
        self,
        benchmark,
        async_db_session: AsyncSession,
        perf_test_movements,
    ):
        """Benchmark counting total movements."""

        async def _count_all():
            from sqlalchemy import func

            result = await async_db_session.execute(
                select(func.count(Movement.id)).where(Movement.is_active.is_(True))
            )
            return result.scalar()

        count = benchmark(_count_all)

        # Verify count
        assert count > 0
