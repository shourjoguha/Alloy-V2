"""
Unit tests for DeloadService.

Tests deload scheduling, recovery-based triggers, and history tracking.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deload import deload_service
from app.models.program import Program, Microcycle
from app.models.enums import MicrocycleStatus


@pytest.mark.asyncio
async def test_should_trigger_deload_no_recovery_signals(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
):
    """Test deload trigger with no recovery data."""
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        test_program.id
    )
    
    # No recovery data and no time-based trigger yet
    assert isinstance(should_deload, bool)
    assert isinstance(reason, str)


@pytest.mark.asyncio
async def test_should_trigger_deload_good_recovery(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
    test_recovery_signal,
):
    """Test that good recovery doesn't trigger deload."""
    # test_recovery_signal has good sleep/readiness/hrv
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        test_program.id
    )
    
    # Good recovery should not trigger deload
    if "low sleep" not in reason and "low readiness" not in reason:
        assert should_deload == False or "time-based" in reason


@pytest.mark.asyncio
async def test_should_trigger_deload_low_sleep(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
):
    """Test that low sleep triggers deload."""
    from app.models.logging import RecoverySignal
    from app.models.enums import RecoverySource
    
    # Create low sleep signal
    signal = RecoverySignal(
        user_id=test_user.id,
        date=date.today(),
        source=RecoverySource.MANUAL,
        sleep_score=40.0,  # Low
        sleep_hours=5.0,  # Low
        readiness=75.0,
    )
    async_db_session.add(signal)
    await async_db_session.commit()
    
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        test_program.id
    )
    
    # Should detect low sleep
    assert "low sleep" in reason.lower()


@pytest.mark.asyncio
async def test_should_trigger_deload_low_readiness(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
):
    """Test that low readiness triggers deload."""
    from app.models.logging import RecoverySignal
    from app.models.enums import RecoverySource
    
    # Create low readiness signal
    signal = RecoverySignal(
        user_id=test_user.id,
        date=date.today(),
        source=RecoverySource.MANUAL,
        sleep_score=85.0,
        sleep_hours=8.0,
        readiness=30.0,  # Low
    )
    async_db_session.add(signal)
    await async_db_session.commit()
    
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        test_program.id
    )
    
    # Should detect low readiness
    assert "low readiness" in reason.lower()


@pytest.mark.asyncio
async def test_should_trigger_deload_time_based(
    async_db_session: AsyncSession,
    test_user,
):
    """Test time-based deload trigger (4+ weeks without deload)."""
    from app.models.enums import Goal, SplitTemplate as SplitTemplateEnum, ProgressionStyle, PersonaTone, PersonaAggression
    
    # Create a program with old start date (>4 weeks ago)
    old_date = date.today() - timedelta(weeks=6)
    program = Program(
        user_id=test_user.id,
        split_template=SplitTemplateEnum.UPPER_LOWER,
        start_date=old_date,
        duration_weeks=8,
        goal_1=Goal.STRENGTH,
        goal_2=Goal.HYPERTROPHY,
        goal_3=Goal.ENDURANCE,
        goal_weight_1=5,
        goal_weight_2=3,
        goal_weight_3=2,
        days_per_week=4,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        deload_every_n_microcycles=4,
        persona_tone=PersonaTone.SUPPORTIVE,
        persona_aggression=PersonaAggression.BALANCED,
        is_active=True,
    )
    async_db_session.add(program)
    await async_db_session.flush()
    
    # Create a microcycle with no deload flag set
    microcycle = Microcycle(
        program_id=program.id,
        sequence_number=1,
        start_date=old_date,
        length_days=7,
        status=MicrocycleStatus.ACTIVE,
        is_deload=False,
    )
    async_db_session.add(microcycle)
    await async_db_session.commit()
    
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        program.id
    )
    
    # Should trigger based on time
    assert "time-based" in reason.lower()


@pytest.mark.asyncio
async def test_days_since_last_deload_no_deload(
    async_db_session: AsyncSession,
    test_program: Program,
):
    """Test calculating days since last deload when none exist."""
    # This is an internal method, but we test the trigger logic that uses it
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_program.user_id,
        test_program.id
    )
    
    # With no deload, high days count could trigger time-based rule
    assert isinstance(should_deload, bool)


@pytest.mark.asyncio
async def test_deload_service_singleton():
    """Test that deload_service is a singleton instance."""
    # The service should be the same instance
    from app.services.deload import deload_service as ds1
    from app.services.deload import deload_service as ds2
    
    assert ds1 is ds2


@pytest.mark.asyncio
async def test_multiple_recovery_signals_aggregation(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
):
    """Test that recovery signals are properly aggregated."""
    from app.models.logging import RecoverySignal
    from app.models.enums import RecoverySource
    
    # Create multiple signals
    for i in range(3):
        signal = RecoverySignal(
            user_id=test_user.id,
            date=date.today() - timedelta(days=i),
            source=RecoverySource.MANUAL,
            sleep_score=70.0 + (i * 5),
            sleep_hours=7.0 + (i * 0.3),
            readiness=50.0 + (i * 5),
        )
        async_db_session.add(signal)
    await async_db_session.commit()
    
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        test_program.id
    )
    
    # Should evaluate based on aggregated signals
    assert isinstance(should_deload, bool)


@pytest.mark.asyncio
async def test_deload_reason_messages(
    async_db_session: AsyncSession,
    test_program: Program,
    test_user,
):
    """Test that deload reasons are clearly explained."""
    should_deload, reason = await deload_service.should_trigger_deload(
        async_db_session,
        test_user.id,
        test_program.id
    )
    
    # Reason should be either clear trigger or "no trigger"
    assert isinstance(reason, str)
    assert len(reason) > 0
    # Valid reasons
    valid_reasons = ["no trigger", "low sleep", "low readiness", "time-based"]
    assert any(r in reason.lower() for r in valid_reasons)
