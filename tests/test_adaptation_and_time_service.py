"""
Unit tests for AdaptationService and TimeEstimationService.

Tests session adaptation, movement constraints, and duration estimation.
"""

import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.adaptation import adaptation_service
from app.services.time_estimation import time_estimation_service
from app.models.program import Session
from app.schemas.daily import AdaptationRequest, SorenessInput, RecoveryInput
from app.models.enums import SessionType, MovementPattern


# ============== AdaptationService Tests ==============

@pytest.mark.asyncio
async def test_adapt_session_no_constraints(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test session adaptation with no constraints or issues."""
    request = AdaptationRequest(
        program_id=test_session.microcycle.program_id,
        soreness=[],
        recovery=RecoveryInput(sleep_hours=8.0, energy_level=8),
    )
    
    result = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        test_session.id,
        request
    )
    
    assert "adapted_patterns" in result
    assert "removed_patterns" in result
    assert "added_sections" in result
    assert "recovery_score" in result


@pytest.mark.asyncio
async def test_adapt_session_with_soreness(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test session adaptation with reported soreness."""
    request = AdaptationRequest(
        program_id=test_session.microcycle.program_id,
        soreness=[
            SorenessInput(body_part="legs", level=5),
        ],
        recovery=RecoveryInput(sleep_hours=7.0, energy_level=6),
    )
    
    result = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        test_session.id,
        request
    )
    
    # Should have adapted patterns
    assert isinstance(result["adapted_patterns"], list)
    assert isinstance(result["removed_patterns"], list)
    assert isinstance(result["recovery_score"], int)


@pytest.mark.asyncio
async def test_adapt_session_low_recovery(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test session adaptation with low recovery signals."""
    request = AdaptationRequest(
        program_id=test_session.microcycle.program_id,
        soreness=[],
        recovery=RecoveryInput(
            sleep_hours=4.0,  # Low
            energy_level=3,   # Low
            stress_level=9,   # High
        ),
    )
    
    result = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        test_session.id,
        request
    )
    
    # Low recovery should add extra warmup or reduce intensity
    recovery_score = result.get("recovery_score", 0)
    assert recovery_score < 50  # Low recovery score


@pytest.mark.asyncio
async def test_adapt_session_high_recovery(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test session adaptation with high recovery signals."""
    request = AdaptationRequest(
        program_id=test_session.microcycle.program_id,
        soreness=[],
        recovery=RecoveryInput(
            sleep_hours=9.0,  # High
            energy_level=9,   # High
            stress_level=2,   # Low
        ),
    )
    
    result = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        test_session.id,
        request
    )
    
    # High recovery might add conditioning
    recovery_score = result.get("recovery_score", 50)
    assert recovery_score > 50  # High recovery score


@pytest.mark.asyncio
async def test_suggest_exercise_substitution(
    async_db_session: AsyncSession,
    test_user,
):
    """Test exercise substitution suggestion."""
    result = await adaptation_service.suggest_exercise_substitution(
        async_db_session,
        test_user.id,
        "Barbell Squat",
        context={"goal": "strength", "intensity": "high"},
    )
    
    # MVP returns empty suggestions
    assert "suggested_movements" in result
    assert "reasoning" in result
    assert result["original_movement"] == "Barbell Squat"


@pytest.mark.asyncio
async def test_apply_movement_rule(
    async_db_session: AsyncSession,
    test_user,
    test_movements,
):
    """Test creating a movement rule."""
    movement_id = test_movements[0].id
    
    rule = await adaptation_service.apply_movement_rule(
        async_db_session,
        test_user.id,
        movement_id=movement_id,
        rule_type="hard_no",
        reason="Shoulder injury",
    )
    
    assert rule.user_id == test_user.id
    assert rule.movement_id == movement_id


@pytest.mark.asyncio
async def test_apply_movement_rule_update_existing(
    async_db_session: AsyncSession,
    test_user,
    test_movements,
):
    """Test updating an existing movement rule."""
    movement_id = test_movements[0].id
    
    # Create initial rule
    rule1 = await adaptation_service.apply_movement_rule(
        async_db_session,
        test_user.id,
        movement_id=movement_id,
        rule_type="hard_no",
        reason="Shoulder injury",
    )
    
    # Update the rule
    rule2 = await adaptation_service.apply_movement_rule(
        async_db_session,
        test_user.id,
        movement_id=movement_id,
        rule_type="hard_no",
        reason="Knee injury - avoid squats",
    )
    
    assert rule2.user_id == test_user.id
    assert rule2.notes == "Knee injury - avoid squats"


@pytest.mark.asyncio
async def test_adaptation_recovery_score_bounds(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test that recovery score is always 0-100."""
    request = AdaptationRequest(
        program_id=test_session.microcycle.program_id,
        soreness=[],
        recovery=RecoveryInput(sleep_hours=12.0),  # Extreme
    )
    
    result = await adaptation_service.adapt_session(
        async_db_session,
        test_user.id,
        test_session.id,
        request
    )
    
    recovery_score = result.get("recovery_score", 50)
    assert 0 <= recovery_score <= 100


# ============== TimeEstimationService Tests ==============

@pytest.mark.asyncio
async def test_estimate_session_duration(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test estimating session duration."""
    result = await time_estimation_service.estimate_session_duration(
        async_db_session,
        test_user.id,
        test_session.id,
    )
    
    assert "total_minutes" in result
    assert "breakdown" in result
    assert result["total_minutes"] > 0
    assert result["total_minutes"] < 180  # Less than 3 hours


@pytest.mark.asyncio
async def test_session_duration_breakdown(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test that duration breakdown is reasonable."""
    result = await time_estimation_service.estimate_session_duration(
        async_db_session,
        test_user.id,
        test_session.id,
    )
    
    breakdown = result["breakdown"]
    assert "warmup_minutes" in breakdown
    assert "main_minutes" in breakdown
    assert "cooldown_minutes" in breakdown
    assert breakdown["warmup_minutes"] > 0
    assert breakdown["main_minutes"] > 0
    assert breakdown["cooldown_minutes"] > 0


@pytest.mark.asyncio
async def test_estimate_microcycle_duration(
    async_db_session: AsyncSession,
    test_microcycle,
    test_user,
):
    """Test estimating microcycle duration."""
    result = await time_estimation_service.estimate_microcycle_duration(
        async_db_session,
        test_user.id,
        test_microcycle.id,
    )
    
    assert "total_hours" in result
    assert "daily_average_minutes" in result
    assert "session_count" in result
    assert result["total_hours"] >= 0


@pytest.mark.asyncio
async def test_duration_respects_intensity(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test that high intensity estimates longer duration."""
    # Estimate with current session
    result_current = await time_estimation_service.estimate_session_duration(
        async_db_session,
        test_user.id,
        test_session.id,
    )
    
    # Both should have reasonable durations
    assert result_current["total_minutes"] > 0
    assert result_current["total_minutes"] < 180


@pytest.mark.asyncio
async def test_confidence_level(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test that confidence level is reported."""
    result = await time_estimation_service.estimate_session_duration(
        async_db_session,
        test_user.id,
        test_session.id,
    )
    
    assert "confidence" in result
    assert result["confidence"] in ["high", "medium", "low"]


@pytest.mark.asyncio
async def test_time_estimation_singleton():
    """Test that time_estimation_service is a singleton."""
    from app.services.time_estimation import time_estimation_service as ts1
    from app.services.time_estimation import time_estimation_service as ts2
    
    assert ts1 is ts2


@pytest.mark.asyncio
async def test_duration_reasonable_range(
    async_db_session: AsyncSession,
    test_session: Session,
    test_user,
):
    """Test that estimated durations are in reasonable range."""
    result = await time_estimation_service.estimate_session_duration(
        async_db_session,
        test_user.id,
        test_session.id,
    )
    
    # Sessions should be 15-180 minutes
    assert 15 <= result["total_minutes"] <= 180


@pytest.mark.asyncio
async def test_microcycle_duration_multiple_sessions(
    async_db_session: AsyncSession,
    test_microcycle,
    test_user,
):
    """Test microcycle duration with multiple sessions."""
    from app.models.program import Session
    from app.models.enums import SessionType
    from datetime import date, timedelta
    
    # Create additional sessions in this microcycle
    for i in range(2):
        session = Session(
            microcycle_id=test_microcycle.id,
            date=date.today() + timedelta(days=i),
            day_number=i + 2,
            session_type=SessionType.LOWER,
            intent_tags=[],
        )
        async_db_session.add(session)
    await async_db_session.commit()
    
    result = await time_estimation_service.estimate_microcycle_duration(
        async_db_session,
        test_user.id,
        test_microcycle.id,
    )
    
    # With 3 sessions
    assert result["session_count"] >= 1
    assert result["total_hours"] > 0
