"""
Unit tests for ProgramService.

Tests program generation, microcycle creation, and goal distribution.
"""

import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.program import program_service
from app.models.program import Program, Microcycle
from app.models.enums import Goal, SplitTemplate as SplitTemplateEnum, ProgressionStyle, MicrocycleStatus
from app.schemas.program import ProgramCreate, GoalWeight
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_create_program_valid(async_db_session: AsyncSession, test_user):
    """Test creating a valid 8-week program."""
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=8,
        program_start_date=date.today(),  # Mapped to start_date by schema
        split_template=SplitTemplateEnum.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    assert program.id is not None
    assert program.user_id == test_user.id
    assert program.duration_weeks == 8
    assert program.is_active == True


@pytest.mark.asyncio
async def test_create_program_generates_microcycles(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that creating a program generates microcycles."""
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=8,
        program_start_date=date.today(),
        split_template=SplitTemplateEnum.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    # 8 weeks = 8 microcycles (1 week each)
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = list(result.scalars().all())
    
    assert len(microcycles) == 4
    assert all(mc.program_id == program.id for mc in microcycles)


@pytest.mark.asyncio
async def test_create_program_deload_placement(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that deloads are placed every 4 microcycles."""
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=12,  # 6 microcycles
        program_start_date=date.today(),
        split_template=SplitTemplateEnum.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = sorted(list(result.scalars().all()), key=lambda m: m.sequence_number)
    
    # Deload should be at index 3 (4th microcycle)
    if len(microcycles) >= 4:
        assert microcycles[3].is_deload == True
        assert microcycles[0].is_deload == False
        assert microcycles[1].is_deload == False
        assert microcycles[2].is_deload == False


@pytest.mark.asyncio
async def test_create_program_invalid_week_count_too_short(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that program with < 8 weeks is rejected."""
    with pytest.raises(ValidationError):
        ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=6,  # Too short
            program_start_date=date.today(),
            split_template=SplitTemplateEnum.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )


@pytest.mark.asyncio
async def test_create_program_invalid_week_count_too_long(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that program with > 12 weeks is rejected."""
    with pytest.raises(ValidationError):
        ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=16,  # Too long
            program_start_date=date.today(),
            split_template=SplitTemplateEnum.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )


@pytest.mark.asyncio
async def test_create_program_invalid_week_count_odd(async_db_session: AsyncSession, test_user):
    with pytest.raises(ValidationError):
        ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=9,
            program_start_date=date.today(),
            split_template=SplitTemplateEnum.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )


@pytest.mark.asyncio
async def test_get_program(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
):
    """Test retrieving a program."""
    result = await program_service.get_program(
        async_db_session,
        test_program.id,
        test_user.id
    )
    
    assert result is not None
    assert result.id == test_program.id
    assert result.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_program_not_found(async_db_session: AsyncSession, test_user):
    """Test retrieving a nonexistent program."""
    result = await program_service.get_program(
        async_db_session,
        999,  # Nonexistent ID
        test_user.id
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_list_programs_empty(async_db_session: AsyncSession, test_user):
    """Test listing programs when none exist."""
    result = await program_service.list_programs(async_db_session, test_user.id)
    
    assert result == []


@pytest.mark.asyncio
async def test_list_programs_multiple(
    async_db_session: AsyncSession,
    test_user,
):
    """Test listing multiple programs."""
    # Create 2 programs
    for i in range(2):
        request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=8,
            program_start_date=date.today(),
            split_template=SplitTemplateEnum.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
        await program_service.create_program(async_db_session, test_user.id, request)
    
    result = await program_service.list_programs(async_db_session, test_user.id)
    
    assert len(result) == 2


@pytest.mark.asyncio
async def test_microcycle_sequences_ordered(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that microcycles have correct sequence numbers."""
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=8,
        program_start_date=date.today(),
        split_template=SplitTemplateEnum.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = sorted(list(result.scalars().all()), key=lambda m: m.sequence_number)
    
    # Check sequence numbers are 1, 2, 3, 4
    for i, mc in enumerate(microcycles, start=1):
        assert mc.sequence_number == i


@pytest.mark.asyncio
async def test_microcycle_dates_sequential(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that microcycle dates are sequential (14 days apart)."""
    from datetime import timedelta
    
    start_date = date.today()
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=8,
        program_start_date=start_date,
        split_template=SplitTemplateEnum.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = sorted(list(result.scalars().all()), key=lambda m: m.sequence_number)
    
    for i, mc in enumerate(microcycles):
        expected_date = start_date + timedelta(days=14 * i)
        assert mc.start_date == expected_date


@pytest.mark.asyncio
async def test_program_goals_stored_correctly(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that program goals and weights are stored correctly."""
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=8,
        program_start_date=date.today(),
        split_template=SplitTemplateEnum.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )

    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    assert program.goal_1 == Goal.STRENGTH
    assert program.goal_2 == Goal.HYPERTROPHY
    assert program.goal_3 == Goal.ENDURANCE
    assert program.goal_weight_1 == 5
    assert program.goal_weight_2 == 3
    assert program.goal_weight_3 == 2
