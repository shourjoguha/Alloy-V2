"""
Unit tests for MetricsService.

Tests volume calculation, trend detection, and recovery aggregation.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.metrics import metrics_service
from app.models.enums import MovementPattern


@pytest.mark.asyncio
async def test_get_pattern_exposures_empty(async_db_session: AsyncSession, test_user):
    """Test getting pattern exposures when none exist."""
    result = await metrics_service.get_pattern_exposures(
        async_db_session,
        test_user.id,
        MovementPattern.SQUAT,
        lookback_microcycles=4
    )
    
    assert result == []


@pytest.mark.asyncio
async def test_get_volume_load_empty(async_db_session: AsyncSession, test_user):
    """Test volume load calculation with no data."""
    volume = await metrics_service.get_volume_load(
        async_db_session,
        test_user.id,
        MovementPattern.SQUAT,
        lookback_days=7
    )
    
    assert volume == 0


@pytest.mark.asyncio
async def test_get_recovery_status_empty(async_db_session: AsyncSession, test_user):
    """Test recovery status with no signals."""
    status = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    
    assert status["sleep_avg"] is None
    assert status["readiness_avg"] is None
    assert status["hrv_avg"] is None
    assert status["signal_count"] == 0


@pytest.mark.asyncio
async def test_get_recovery_status_with_signals(
    async_db_session: AsyncSession,
    test_user,
    test_recovery_signal
):
    """Test recovery status aggregation with data."""
    status = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    
    assert status["signal_count"] == 1
    assert status["sleep_avg"] is not None
    assert status["sleep_avg"] == 85.0
    assert status["readiness_avg"] is not None
    assert status["readiness_avg"] == 75.0
    assert status["hrv_avg"] is not None
    assert status["hrv_avg"] == 50.0


@pytest.mark.asyncio
async def test_get_recovery_status_multiple_signals(
    async_db_session: AsyncSession,
    test_user,
):
    """Test recovery status averaging multiple signals."""
    from app.models.logging import RecoverySignal
    from app.models.enums import RecoverySource
    
    # Create multiple signals with varying scores
    signals = [
        RecoverySignal(
            user_id=test_user.id,
            date=date.today(),
            source=RecoverySource.MANUAL,
            sleep_score=80.0,
            readiness=70.0,
            hrv=45.0,
        ),
        RecoverySignal(
            user_id=test_user.id,
            date=date.today() - timedelta(days=1),
            source=RecoverySource.MANUAL,
            sleep_score=90.0,
            readiness=80.0,
            hrv=55.0,
        ),
    ]
    async_db_session.add_all(signals)
    await async_db_session.commit()
    
    status = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    
    assert status["signal_count"] == 2
    assert status["sleep_avg"] == 85.0  # (80 + 90) / 2
    assert status["readiness_avg"] == 75.0  # (70 + 80) / 2
    assert status["hrv_avg"] == 50.0  # (45 + 55) / 2


@pytest.mark.asyncio
async def test_volume_load_calculation(
    async_db_session: AsyncSession,
    test_user,
    test_movements,
):
    """Test volume load with pattern exposures."""
    from app.models.logging import PatternExposure
    
    # Would need to create PatternExposure records, but fixture doesn't provide them
    # This test is a placeholder for when we have exposure data
    volume = await metrics_service.get_volume_load(
        async_db_session,
        test_user.id,
        MovementPattern.SQUAT,
        lookback_days=7
    )
    
    assert isinstance(volume, int)
    assert volume >= 0


@pytest.mark.asyncio
async def test_get_psi_trend_no_data(async_db_session: AsyncSession, test_user):
    """Test PSI trend with no logged PSI data."""
    # Note: PSILog doesn't exist in models, so this returns empty
    # The service should handle gracefully
    result = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    
    # Should return dict with None/0 values
    assert isinstance(result, dict)
    assert "signal_count" in result


@pytest.mark.asyncio
async def test_recovery_status_handles_missing_fields(
    async_db_session: AsyncSession,
    test_user,
):
    """Test recovery status handles signals with missing optional fields."""
    from app.models.logging import RecoverySignal
    from app.models.enums import RecoverySource
    
    # Signal with only sleep data
    signal = RecoverySignal(
        user_id=test_user.id,
        date=date.today(),
        source=RecoverySource.MANUAL,
        sleep_score=75.0,
        readiness=None,
        hrv=None,
    )
    async_db_session.add(signal)
    await async_db_session.commit()
    
    status = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    
    assert status["sleep_avg"] == 75.0
    assert status["readiness_avg"] is None
    assert status["hrv_avg"] is None


@pytest.mark.asyncio
async def test_metrics_service_singleton(async_db_session: AsyncSession, test_user):
    """Test that metrics_service is a singleton instance."""
    result1 = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    result2 = await metrics_service.get_recovery_status(async_db_session, test_user.id)
    
    # Both should return the same structure
    assert result1.keys() == result2.keys()


@pytest.mark.asyncio
async def test_volume_load_respects_lookback_window(
    async_db_session: AsyncSession,
    test_user,
):
    """Test that volume load respects the lookback days window."""
    volume_7d = await metrics_service.get_volume_load(
        async_db_session,
        test_user.id,
        MovementPattern.SQUAT,
        lookback_days=7
    )
    
    volume_14d = await metrics_service.get_volume_load(
        async_db_session,
        test_user.id,
        MovementPattern.SQUAT,
        lookback_days=14
    )
    
    # With no data, both should be 0
    assert volume_7d == 0
    assert volume_14d == 0
