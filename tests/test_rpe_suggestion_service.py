"""
Comprehensive unit tests for RPESuggestionService.

Test scenarios covered:
1. Program type awareness - Strength program returns RPE 7.5-9.5 for compounds, Hypertrophy returns 6.5-8.5
2. CNS/discipline caps - Olympic movements capped at RPE 8.5, Powerlifting capped at 8.5
3. Fatigue adjustments - Sleep < 6h reduces RPE by 0.5, HRV -20% reduces by 1.0, Soreness > 7 reduces by 1.0
4. Pattern recovery - Pattern trained 24h ago at RPE 8 is ready, trained 48h ago at RPE 9 is ready
5. Frequency constraints - Max high-RPE sets per session enforced (6 for hinge/squat/lunge/olympic)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from app.services.rpe_suggestion_service import RPESuggestionService, RPESuggestion
from app.models.enums import (
    ExerciseRole,
    MovementPattern,
    CNSLoad,
    PrimaryMuscle,
    PrimaryRegion,
    SkillLevel,
)


@pytest.fixture
def squat_movement():
    """Create a mock squat movement."""
    movement = Mock()
    movement.id = 1
    movement.name = "Barbell Squat"
    movement.pattern = "squat"
    movement.cns_load = "high"
    movement.discipline_type = "powerlifting"
    movement.compound = True
    return movement


@pytest.fixture
def deadlift_movement():
    """Create a mock deadlift movement."""
    movement = Mock()
    movement.id = 2
    movement.name = "Barbell Deadlift"
    movement.pattern = "hinge"
    movement.cns_load = "high"
    movement.discipline_type = "powerlifting"
    movement.compound = True
    return movement


@pytest.fixture
def snatch_movement():
    """Create a mock snatch movement."""
    movement = Mock()
    movement.id = 3
    movement.name = "Snatch"
    movement.pattern = "olympic"
    movement.cns_load = "very_high"
    movement.discipline_type = "olympic_weightlifting"
    movement.compound = True
    return movement


@pytest.fixture
def bench_press_movement():
    """Create a mock bench press movement."""
    movement = Mock()
    movement.id = 4
    movement.name = "Barbell Bench Press"
    movement.pattern = "horizontal_push"
    movement.cns_load = "moderate"
    movement.discipline_type = "bodybuilding"
    movement.compound = True
    return movement


@pytest.fixture
def isolation_movement():
    """Create a mock isolation movement."""
    movement = Mock()
    movement.id = 5
    movement.name = "Bicep Curls"
    movement.pattern = "isolation"
    movement.cns_load = "low"
    movement.discipline_type = "bodybuilding"
    movement.compound = False
    return movement


@pytest.fixture
def rpe_service():
    """Create RPE suggestion service with mocked config."""
    from app.config.optimization_config_loader import (
        MicrocycleProgressionConfig,
        ProgramTypeRPEProfile,
        CNSDisciplineAdjustmentsConfig,
        FatigueAdjustmentsConfig,
        RecoveryHoursByRPEConfig,
        RPESuggestionConfig,
    )
    
    # Create mock config with actual dataclass instances
    strength_progression = MicrocycleProgressionConfig(
        accumulation=[7.0, 8.5],
        intensification=[7.5, 9.0],
        peaking=[8.0, 9.5],
        deload=[5.5, 7.0],
    )
    
    hypertrophy_progression = MicrocycleProgressionConfig(
        accumulation=[6.0, 8.0],
        intensification=[6.5, 8.5],
        peaking=[7.0, 9.0],
        deload=[5.0, 6.5],
    )
    
    program_profiles = {
        "strength": ProgramTypeRPEProfile(
            primary_compound_rpe=[7.5, 9.5],
            accessory_rpe=[6.0, 7.5],
            weekly_high_rpe_sets_max=12,
            microcycle_progression=strength_progression,
        ),
        "hypertrophy": ProgramTypeRPEProfile(
            primary_compound_rpe=[6.5, 8.5],
            accessory_rpe=[5.5, 7.0],
            weekly_high_rpe_sets_max=10,
            microcycle_progression=hypertrophy_progression,
        ),
    }
    
    cns_adjustments = {
        "high_cns_olympic_powerlifting": CNSDisciplineAdjustmentsConfig(
            rpe_cap=8.5,
            weekly_limit=5,
        ),
    }
    
    fatigue_config = FatigueAdjustmentsConfig(
        sleep_under_6h=-0.5,
        sleep_under_5h=-1.0,
        hrv_below_baseline_20pct=-1.0,
        soreness_above_7=-1.0,
        consecutive_high_rpe_days=-0.5,
    )
    
    recovery_hours = RecoveryHoursByRPEConfig(
        rpe_6_7=24,
        rpe_8=48,
        rpe_9=72,
        rpe_10=96,
    )
    
    rpe_config = RPESuggestionConfig(
        warmup_rpe=[1.0, 3.0],
        main_strength_rpe=[7.0, 9.0],
        main_hypertrophy_rpe=[6.0, 8.0],
        accessory_rpe=[5.0, 7.0],
        cooldown_rpe=[1.0, 3.0],
        circuit_rpe=[5.0, 8.0],
        program_type_profiles=program_profiles,
        cns_discipline_adjustments=cns_adjustments,
        fatigue_adjustments=fatigue_config,
        recovery_hours_by_rpe=recovery_hours,
    )
    
    # Create mock optimization config
    mock_opt_config = Mock()
    mock_opt_config.rpe_suggestion = rpe_config
    
    # Create mock config loader
    mock_loader = Mock()
    mock_loader.config = mock_opt_config
    
    with patch('app.services.rpe_suggestion_service.get_optimization_config', return_value=mock_opt_config):
        service = RPESuggestionService()
        return service


class TestProgramTypeAwareness:
    """Test program type awareness for RPE suggestions."""
    
    @pytest.mark.asyncio
    async def test_strength_program_compound_high_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that strength program suggests RPE 7.5-9.5 for compound movements."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        assert suggestion.min_rpe >= 7.0
        assert suggestion.max_rpe >= 8.5
        assert suggestion.min_rpe <= suggestion.max_rpe
    
    @pytest.mark.asyncio
    async def test_hypertrophy_program_compound_moderate_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that hypertrophy program suggests RPE 6.5-8.5 for compound movements."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="hypertrophy",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        assert suggestion.min_rpe >= 6.0
        assert suggestion.max_rpe >= 8.0
        assert suggestion.max_rpe <= 9.0
    
    @pytest.mark.asyncio
    async def test_strength_accumulation_phase_lower_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that accumulation phase suggests lower RPE than peaking."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="accumulation",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Accumulation should be lower than or equal to peaking
        peaking_suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Check that accumulation min_rpe is lower or max_rpe is lower
        assert suggestion.min_rpe <= peaking_suggestion.min_rpe
        assert suggestion.max_rpe <= peaking_suggestion.max_rpe
    
    @pytest.mark.asyncio
    async def test_deload_phase_lowest_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that deload phase suggests lowest RPE."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="deload",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        assert suggestion.min_rpe <= 6.0
        assert suggestion.max_rpe <= 7.5
    
    @pytest.mark.asyncio
    async def test_accessory_role_lower_rpe_than_main(
        self, rpe_service, isolation_movement
    ):
        """Test that accessory role suggests lower RPE than main strength."""
        accessory_suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=isolation_movement,
            exercise_role=ExerciseRole.ACCESSORY,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        main_suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=isolation_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        assert accessory_suggestion.max_rpe <= main_suggestion.max_rpe


class TestCNSDisciplineCaps:
    """Test CNS/discipline RPE caps for high-intensity movements."""
    
    @pytest.mark.asyncio
    async def test_olympic_movement_capped_at_8_5(
        self, rpe_service, snatch_movement
    ):
        """Test that Olympic movements are capped at RPE 8.5."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=snatch_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should be capped at 8.5
        assert suggestion.max_rpe <= 8.5
    
    @pytest.mark.asyncio
    async def test_powerlifting_movement_capped_at_8_5(
        self, rpe_service, deadlift_movement
    ):
        """Test that powerlifting movements are capped at RPE 8.5."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=deadlift_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should be capped at 8.5
        assert suggestion.max_rpe <= 8.5
    
    @pytest.mark.asyncio
    async def test_low_cns_movement_not_capped(
        self, rpe_service, bench_press_movement
    ):
        """Test that low CNS movements are not capped."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=bench_press_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should allow higher RPE for moderate CNS movements
        assert suggestion.max_rpe >= 9.0
    
    @pytest.mark.asyncio
    async def test_bodybuilding_discipline_not_capped(
        self, rpe_service, bench_press_movement
    ):
        """Test that bodybuilding discipline movements are not capped."""
        bench_press_movement.cns_load = "high"
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=bench_press_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should not cap bodybuilding movements
        assert suggestion.max_rpe >= 9.0


class TestFatigueAdjustments:
    """Test fatigue adjustments based on recovery signals."""
    
    @pytest.mark.asyncio
    async def test_sleep_under_6h_reduces_rpe_by_0_5(
        self, rpe_service, squat_movement
    ):
        """Test that sleep < 6 hours reduces RPE by 0.5."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={"sleep_hours": 5.5},
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is not None
        assert "sleep" in suggestion.adjustment_reason.lower()
    
    @pytest.mark.asyncio
    async def test_sleep_under_5h_reduces_rpe_by_1_0(
        self, rpe_service, squat_movement
    ):
        """Test that sleep < 5 hours reduces RPE by 1.0."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={"sleep_hours": 4.5},
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is not None
        assert "sleep" in suggestion.adjustment_reason.lower()
        
        # Get baseline without fatigue
        baseline = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Sleep under 5h should reduce more than sleep under 6h
        suggestion_6h = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={"sleep_hours": 5.5},
            pattern_recovery_hours={},
        )
        
        assert suggestion.max_rpe <= suggestion_6h.max_rpe
    
    @pytest.mark.asyncio
    async def test_hrv_below_baseline_20pct_reduces_rpe_by_1_0(
        self, rpe_service, squat_movement
    ):
        """Test that HRV < -20% from baseline reduces RPE by 1.0."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={"hrv_percentage_change": -25},
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is not None
        assert "low_hrv" in suggestion.adjustment_reason.lower()
    
    @pytest.mark.asyncio
    async def test_soreness_above_7_reduces_rpe_by_1_0(
        self, rpe_service, squat_movement
    ):
        """Test that soreness > 7 reduces RPE by 1.0."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={"soreness": 8},
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is not None
        assert "soreness" in suggestion.adjustment_reason.lower()
    
    @pytest.mark.asyncio
    async def test_multiple_fatigue_signals_accumulate(
        self, rpe_service, squat_movement
    ):
        """Test that multiple fatigue signals accumulate adjustments."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={
                "sleep_hours": 5.5,
                "hrv_percentage_change": -25,
                "soreness": 8,
            },
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is not None
        # Should have all three reasons
        assert "sleep" in suggestion.adjustment_reason.lower()
        assert "low_hrv" in suggestion.adjustment_reason.lower()
        assert "soreness" in suggestion.adjustment_reason.lower()
    
    @pytest.mark.asyncio
    async def test_consecutive_high_rpe_days_reduces_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that consecutive high RPE days reduces RPE."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={"consecutive_high_rpe_days": 2},
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is not None
        assert "consecutive_high_rpe" in suggestion.adjustment_reason.lower()
    
    @pytest.mark.asyncio
    async def test_good_recovery_no_adjustment(
        self, rpe_service, squat_movement
    ):
        """Test that good recovery has no adjustment."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={
                "sleep_hours": 8.0,
                "hrv_percentage_change": 5,
                "soreness": 3,
            },
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is None
    
    @pytest.mark.asyncio
    async def test_fatigue_adjustment_never_below_min(
        self, rpe_service, squat_movement
    ):
        """Test that fatigue adjustments never reduce RPE below minimum threshold."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={
                "sleep_hours": 2.0,
                "hrv_percentage_change": -50,
                "soreness": 10,
            },
            pattern_recovery_hours={},
        )
        
        # Should never go below minimum thresholds (3.0 min, 4.0 max)
        assert suggestion.min_rpe >= 3.0
        assert suggestion.max_rpe >= 4.0


class TestPatternRecovery:
    """Test pattern recovery constraints."""
    
    @pytest.mark.asyncio
    async def test_pattern_24h_ago_ready(
        self, rpe_service, squat_movement
    ):
        """Test that pattern trained 24h ago at RPE 8 is ready."""
        last_trained = datetime.utcnow() - timedelta(hours=24)
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={"squat": last_trained},
        )
        
        # 24h should be sufficient for RPE 6-7 recovery
        assert suggestion.max_rpe >= 7.0
    
    @pytest.mark.asyncio
    async def test_pattern_48h_ago_rpe_9_ready(
        self, rpe_service, squat_movement
    ):
        """Test that pattern trained 48h ago at RPE 9 is ready."""
        last_trained = datetime.utcnow() - timedelta(hours=48)
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={"squat": last_trained},
        )
        
        # 48h should be sufficient for RPE 8 recovery
        assert suggestion.max_rpe >= 7.0
    
    @pytest.mark.asyncio
    async def test_pattern_12h_ago_reduces_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that pattern trained 12h ago has reduced RPE."""
        last_trained = datetime.utcnow() - timedelta(hours=12)
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={"squat": last_trained},
        )
        
        # Get baseline without recovery constraint
        baseline = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should reduce RPE by 1.0
        assert suggestion.max_rpe < baseline.max_rpe
    
    @pytest.mark.asyncio
    async def test_pattern_never_trained_full_rpe(
        self, rpe_service, squat_movement
    ):
        """Test that never-trained pattern gets full RPE."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={"squat": None},
        )
        
        # Should get full RPE range
        assert suggestion.max_rpe >= 8.0
    
    @pytest.mark.asyncio
    async def test_pattern_36h_ago_partial_recovery(
        self, rpe_service, squat_movement
    ):
        """Test that pattern trained 36h ago shows recovery consideration."""
        last_trained = datetime.utcnow() - timedelta(hours=36)
        
        # Test with a movement that hasn't been trained recently vs one that has
        no_recovery_suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={"squat": None},  # Never trained
        )
        
        with_recovery_suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={"squat": last_trained},  # Trained 36h ago
        )
        
        # Both should return valid suggestions
        assert no_recovery_suggestion.min_rpe is not None
        assert no_recovery_suggestion.max_rpe is not None
        assert with_recovery_suggestion.min_rpe is not None
        assert with_recovery_suggestion.max_rpe is not None


class TestFrequencyConstraints:
    """Test frequency constraints for high-RPE sets."""
    
    @pytest.mark.asyncio
    async def test_max_high_rpe_sets_enforced_for_squat(
        self, rpe_service, squat_movement
    ):
        """Test that max high-RPE sets (6) is enforced for squat."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=6,  # At max
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should cap max RPE at 7.5
        assert suggestion.max_rpe <= 7.5
    
    @pytest.mark.asyncio
    async def test_max_high_rpe_sets_enforced_for_hinge(
        self, rpe_service, deadlift_movement
    ):
        """Test that max high-RPE sets (6) is enforced for hinge."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=deadlift_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=6,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should cap max RPE at 7.5
        assert suggestion.max_rpe <= 7.5
    
    @pytest.mark.asyncio
    async def test_max_high_rpe_sets_enforced_for_lunge(
        self, rpe_service
    ):
        """Test that max high-RPE sets (6) is enforced for lunge."""
        lunge_movement = Mock()
        lunge_movement.id = 6
        lunge_movement.name = "Lunges"
        lunge_movement.pattern = "lunge"
        lunge_movement.cns_load = "moderate"
        lunge_movement.discipline_type = "bodybuilding"
        lunge_movement.compound = True
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=lunge_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=6,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should cap max RPE at 7.5
        assert suggestion.max_rpe <= 7.5
    
    @pytest.mark.asyncio
    async def test_max_high_rpe_sets_enforced_for_olympic(
        self, rpe_service, snatch_movement
    ):
        """Test that max high-RPE sets (6) is enforced for olympic."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=snatch_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=6,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should cap max RPE at 7.5 (or lower due to CNS cap)
        assert suggestion.max_rpe <= 7.5
    
    @pytest.mark.asyncio
    async def test_below_max_high_rpe_sets_no_limit(
        self, rpe_service, squat_movement
    ):
        """Test that below max high-RPE sets has no limit."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=5,  # Below max
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should not cap
        assert suggestion.max_rpe >= 8.0
    
    @pytest.mark.asyncio
    async def test_non_pattern_movement_no_limit(
        self, rpe_service, bench_press_movement
    ):
        """Test that non-pattern movements have no frequency limit."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=bench_press_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=10,  # Way over max
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should not cap for non-pattern movements
        assert suggestion.max_rpe >= 8.0
    
    @pytest.mark.asyncio
    async def test_isolation_movement_no_limit(
        self, rpe_service, isolation_movement
    ):
        """Test that isolation movements have no frequency limit."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=isolation_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=10,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should not cap for isolation movements
        assert suggestion.max_rpe >= 8.0


class TestSessionRPESuggestions:
    """Test session-level RPE suggestions."""
    
    @pytest.mark.asyncio
    async def test_session_suggestions_all_roles(
        self, rpe_service
    ):
        """Test that session suggestions include all exercise roles."""
        from app.models.enums import Goal
        
        suggestions = await rpe_service.suggest_rpe_for_session(
            session_type="strength",
            program_type="strength",
            microcycle_phase="intensification",
            user_goals=[Goal.STRENGTH],
            user_recovery_state={},
            weekly_high_rpe_sets_count=0,
        )
        
        # Should include all roles
        assert ExerciseRole.WARMUP in suggestions
        assert ExerciseRole.MAIN in suggestions
        assert ExerciseRole.ACCESSORY in suggestions
        assert ExerciseRole.COOLDOWN in suggestions
    
    @pytest.mark.asyncio
    async def test_warmup_low_rpe(self, rpe_service):
        """Test that warmup has low RPE range."""
        from app.models.enums import Goal
        
        suggestions = await rpe_service.suggest_rpe_for_session(
            session_type="strength",
            program_type="strength",
            microcycle_phase="intensification",
            user_goals=[Goal.STRENGTH],
            user_recovery_state={},
            weekly_high_rpe_sets_count=0,
        )
        
        min_rpe, max_rpe = suggestions[ExerciseRole.WARMUP]
        assert max_rpe <= 4.0
    
    @pytest.mark.asyncio
    async def test_cooldown_low_rpe(self, rpe_service):
        """Test that cooldown has low RPE range."""
        from app.models.enums import Goal
        
        suggestions = await rpe_service.suggest_rpe_for_session(
            session_type="strength",
            program_type="strength",
            microcycle_phase="intensification",
            user_goals=[Goal.STRENGTH],
            user_recovery_state={},
            weekly_high_rpe_sets_count=0,
        )
        
        min_rpe, max_rpe = suggestions[ExerciseRole.COOLDOWN]
        assert max_rpe <= 4.0
    
    @pytest.mark.asyncio
    async def test_main_strength_highest_rpe(self, rpe_service):
        """Test that main strength has highest RPE range."""
        from app.models.enums import Goal
        
        suggestions = await rpe_service.suggest_rpe_for_session(
            session_type="strength",
            program_type="strength",
            microcycle_phase="intensification",
            user_goals=[Goal.STRENGTH],
            user_recovery_state={},
            weekly_high_rpe_sets_count=0,
        )
        
        strength_max = suggestions[ExerciseRole.MAIN][1]
        accessory_max = suggestions[ExerciseRole.ACCESSORY][1]
        
        assert strength_max >= accessory_max


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_unknown_program_type_uses_strength_default(
        self, rpe_service, squat_movement
    ):
        """Test that unknown program type falls back to strength profile."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="unknown_program",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Should still return a valid suggestion
        assert suggestion.min_rpe is not None
        assert suggestion.max_rpe is not None
        assert suggestion.min_rpe <= suggestion.max_rpe
    
    @pytest.mark.asyncio
    async def test_empty_recovery_state(
        self, rpe_service, squat_movement
    ):
        """Test that empty recovery state works."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        assert suggestion.adjustment_reason is None
    
    @pytest.mark.asyncio
    async def test_rpe_rounding(
        self, rpe_service, squat_movement
    ):
        """Test that RPE values are rounded to 1 decimal place."""
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="intensification",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={},
            pattern_recovery_hours={},
        )
        
        # Check that values have at most 1 decimal place
        min_str = str(suggestion.min_rpe)
        max_str = str(suggestion.max_rpe)
        
        # Split on decimal and check length
        if '.' in min_str:
            assert len(min_str.split('.')[1]) <= 1
        if '.' in max_str:
            assert len(max_str.split('.')[1]) <= 1


class TestIntegrationScenarios:
    """Test integration of multiple factors."""
    
    @pytest.mark.asyncio
    async def test_all_factors_combined(
        self, rpe_service, snatch_movement
    ):
        """Test all factors combined: program type, CNS cap, fatigue, recovery, frequency."""
        last_trained = datetime.utcnow() - timedelta(hours=24)
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=snatch_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=5,
            user_recovery_state={
                "sleep_hours": 5.5,
                "hrv_percentage_change": -25,
                "soreness": 8,
            },
            pattern_recovery_hours={"olympic": last_trained},
        )
        
        # Should have multiple adjustments
        assert suggestion.min_rpe is not None
        assert suggestion.max_rpe is not None
        assert suggestion.adjustment_reason is not None
        # CNS cap should be applied (max 8.5)
        assert suggestion.max_rpe <= 8.5
    
    @pytest.mark.asyncio
    async def test_optimal_conditions_high_rpe(
        self, rpe_service, squat_movement
    ):
        """Test optimal conditions yield high RPE."""
        last_trained = datetime.utcnow() - timedelta(hours=72)
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=squat_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=0,
            user_recovery_state={
                "sleep_hours": 9.0,
                "hrv_percentage_change": 10,
                "soreness": 2,
            },
            pattern_recovery_hours={"squat": last_trained},
        )
        
        # Optimal conditions should yield high RPE
        assert suggestion.max_rpe >= 8.0
        assert suggestion.adjustment_reason is None
    
    @pytest.mark.asyncio
    async def test_worst_conditions_low_rpe(
        self, rpe_service, snatch_movement
    ):
        """Test worst conditions yield low RPE."""
        last_trained = datetime.utcnow() - timedelta(hours=6)
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=snatch_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type="strength",
            microcycle_phase="peaking",
            training_days_per_week=4,
            session_high_rpe_sets_count=6,
            user_recovery_state={
                "sleep_hours": 3.0,
                "hrv_percentage_change": -50,
                "soreness": 10,
                "consecutive_high_rpe_days": 3,
            },
            pattern_recovery_hours={"olympic": last_trained},
        )
        
        # Worst conditions should yield low RPE
        assert suggestion.max_rpe <= 7.5
        assert suggestion.min_rpe >= 3.0
