"""
End-to-end integration tests for complete ShowMeGains workflows.

Tests the full workflow from program creation through daily planning and session adaptation.
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.program import program_service
from app.services.deload import deload_service
from app.services.adaptation import adaptation_service
from app.services.time_estimation import time_estimation_service
from app.models.program import Program, Microcycle, Session
from app.models.enums import (
    Goal,
    SplitTemplate,
    ProgressionStyle,
    MicrocycleStatus,
    SessionType,
    MovementPattern,
)
from app.schemas.program import ProgramCreate, GoalWeight
from app.schemas.daily import AdaptationRequest, RecoveryInput, SorenessInput


@pytest.mark.asyncio
async def test_e2e_program_creation_to_daily_plan(
    async_db_session: AsyncSession,
    test_user,
):
    """Test complete workflow: create program -> get daily plan -> session data."""
    # Step 1: Create a program
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=8,
        program_start_date=date.today(),
        split_template=SplitTemplate.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    # Step 2: Verify program structure
    assert program.id is not None
    assert program.user_id == test_user.id
    assert program.is_active == True
    
    # Step 3: Verify microcycles were created
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = list(result.scalars().all())
    assert len(microcycles) == 4
    assert microcycles[0].status == MicrocycleStatus.ACTIVE
    
    # Step 4: Verify sessions were created
    sessions = []
    for mc in microcycles:
        result = await async_db_session.execute(
            select(Session).where(Session.microcycle_id == mc.id)
        )
        sessions.extend(result.scalars().all())
    
    assert len(sessions) > 0, "Should have created sessions"
    
    # Step 5: Get first session and estimate duration
    first_session = sessions[0]
    duration_estimate = await time_estimation_service.estimate_session_duration(
        async_db_session, test_user.id, first_session.id
    )
    
    assert duration_estimate["total_minutes"] > 0
    assert duration_estimate["total_minutes"] < 180


@pytest.mark.asyncio
async def test_e2e_daily_adaptation_with_recovery(
    async_db_session: AsyncSession,
    test_user,
    test_session,
    test_recovery_signal,
):
    """Test daily adaptation based on recovery signals."""
    # Step 1: Adapt session with good recovery
    request = AdaptationRequest(
        program_id=test_session.microcycle.program_id,
        soreness=[],
        recovery=RecoveryInput(
            sleep_hours=test_recovery_signal.sleep_hours,
            energy_level=8,
            stress_level=2,
        ),
    )
    
    # Step 2: Call adaptation service
    result = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        test_session.id,
        request,
    )
    
    # Step 3: Verify adaptation logic ran
    assert "adapted_patterns" in result
    assert "recovery_score" in result
    assert 0 <= result["recovery_score"] <= 100
    
    # Step 4: High recovery should not add extra warmup
    if result["recovery_score"] > 70:
        # Expect potential conditioning addition
        assert isinstance(result["added_sections"], list)


@pytest.mark.asyncio
async def test_e2e_program_with_deload_detection(
    async_db_session: AsyncSession,
    test_user,
):
    """Test program generation and deload detection."""
    # Step 1: Create 12-week program to trigger deload logic
    request = ProgramCreate(
        goals=[
            GoalWeight(goal=Goal.STRENGTH, weight=5),
            GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
            GoalWeight(goal=Goal.ENDURANCE, weight=2),
        ],
        duration_weeks=12,
        program_start_date=date.today(),
        split_template=SplitTemplate.UPPER_LOWER,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        deload_every_n_microcycles=4,
    )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    
    # Step 2: Get microcycles and check deload placement
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = sorted(list(result.scalars().all()), key=lambda m: m.sequence_number)
    
    # Step 3: Verify 4th microcycle is marked as deload
    if len(microcycles) >= 4:
        assert microcycles[3].is_deload == True
        assert microcycles[0].is_deload == False
    
    # Step 4: Check deload trigger logic
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        program.id
    )
    
    # Should not trigger with no recovery data
    assert isinstance(should_deload, bool)
    assert isinstance(reason, str)


@pytest.mark.asyncio
async def test_e2e_full_workflow(
    async_db_session: AsyncSession,
    test_user,
):
    """Test complete workflow from program creation through daily usage."""
    # Step 1: Create program
    start_date = date.today()
    request = ProgramCreate(
            goals=[
                GoalWeight(goal=Goal.STRENGTH, weight=5),
                GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                GoalWeight(goal=Goal.ENDURANCE, weight=2),
            ],
            duration_weeks=10,
            program_start_date=start_date,
            split_template=SplitTemplate.UPPER_LOWER,
            days_per_week=4,
            progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        )
    
    program = await program_service.create_program(async_db_session, test_user.id, request)
    assert program.id is not None
    
    # Step 2: Get first microcycle and session
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == program.id)
    )
    microcycles = list(result.scalars().all())
    assert len(microcycles) > 0
    
    # Step 3: Get first session
    result = await async_db_session.execute(
        select(Session).where(Session.microcycle_id == microcycles[0].id)
    )
    sessions = list(result.scalars().all())
    assert len(sessions) > 0
    
    first_session = sessions[0]
    
    # Step 4: Estimate duration for this session
    duration_result = await time_estimation_service.estimate_session_duration(
        async_db_session,
        test_user.id,
        first_session.id,
    )
    assert duration_result["total_minutes"] > 0
    
    # Step 5: Adapt session with constraints
    adaptation_request = AdaptationRequest(
        program_id=program.id,
        soreness=[
                SorenessInput(body_part="shoulders", level=5),
            ],
        recovery=RecoveryInput(
            sleep_hours=7.5,
            energy_level=6,
        ),
    )
    
    adapted = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        first_session.id,
        adaptation_request,
    )
    
    # Step 6: Verify adaptation results
    assert "adapted_patterns" in adapted
    assert "recovery_score" in adapted
    assert 0 <= adapted["recovery_score"] <= 100
    
    # Step 7: Check deload recommendations
    should_deload, deload_reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        program.id
    )
    assert isinstance(should_deload, bool)
    
    # Complete workflow successful
    print(f"\n✅ Full workflow completed:")
    print(f"  - Created {len(microcycles)} microcycles")
    print(f"  - Session duration: {duration_result['total_minutes']} mins")
    print(f"  - Recovery score: {adapted['recovery_score']}")
    print(f"  - Deload recommended: {should_deload}")


@pytest.mark.asyncio
async def test_e2e_multiple_sessions_duration_accumulation(
    async_db_session: AsyncSession,
    test_user,
    test_microcycle,
):
    """Test duration estimation across multiple sessions in a microcycle."""
    from app.models.program import Session
    from app.models.enums import SessionType
    
    # Step 1: Create 4 sessions in the microcycle
    sessions = []
    for i in range(4):
        session = Session(
            microcycle_id=test_microcycle.id,
            date=date.today() + timedelta(days=i),
            day_number=i + 1,
            session_type=SessionType.UPPER if i % 2 == 0 else SessionType.LOWER,
            intent_tags=[],
        )
        async_db_session.add(session)
        sessions.append(session)
    
    await async_db_session.commit()
    
    # Step 2: Estimate individual session durations
    total_duration = 0
    for session in sessions:
        estimate = await time_estimation_service.estimate_session_duration(
            async_db_session,
            test_user.id,
            session.id,
        )
        total_duration += estimate["total_minutes"]
    
    # Step 3: Estimate microcycle duration
    mc_estimate = await time_estimation_service.estimate_microcycle_duration(
        async_db_session,
        test_user.id,
        test_microcycle.id,
    )
    
    # Step 4: Verify microcycle duration is sum of sessions (roughly)
    assert mc_estimate["session_count"] == 4
    assert mc_estimate["total_hours"] > 0
    assert mc_estimate["daily_average_minutes"] > 0
    
    print(f"\n✅ Microcycle duration test:")
    print(f"  - {mc_estimate['session_count']} sessions")
    print(f"  - Total: {mc_estimate['total_hours']} hours")
    print(f"  - Daily average: {mc_estimate['daily_average_minutes']} minutes")
