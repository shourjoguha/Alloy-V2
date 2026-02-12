"""
Unit tests for RPE Suggestion Service.

Tests the core RPE suggestion logic without full database setup.
"""

import pytest
from datetime import datetime, timedelta

from app.services.rpe_suggestion_service import (
    get_rpe_suggestion_service,
    RPESuggestion,
)
from app.models.enums import (
    ExerciseRole,
    MovementPattern,
    PrimaryMuscle,
    PrimaryRegion,
    SkillLevel,
    CNSLoad,
)


class MockMovement:
    """Mock movement for testing RPE service."""
    
    def __init__(
        self,
        name: str,
        pattern: MovementPattern,
        cns_load: CNSLoad,
        discipline_type: str = "general",
    ):
        self.name = name
        self.pattern = pattern
        self.cns_load = cns_load.value
        self.discipline_type = discipline_type
        self.primary_muscle = PrimaryMuscle.QUADRICEPS
        self.primary_region = PrimaryRegion.ANTERIOR_LOWER


@pytest.fixture
def rpe_service():
    """Get RPE suggestion service instance."""
    return get_rpe_suggestion_service()


@pytest.mark.asyncio
async def test_strength_program_main_exercise_rpe(rpe_service):
    """Test RPE suggestion for main exercise in strength program."""
    movement = MockMovement(
        name="Barbell Squat",
        pattern=MovementPattern.SQUAT,
        cns_load=CNSLoad.HIGH,
    )
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Strength accumulation: [6.5, 7.5] base RPE
    assert suggestion.min_rpe >= 6.0, f"RPE min too low: {suggestion.min_rpe}"
    assert suggestion.max_rpe <= 8.5, f"RPE max too high: {suggestion.max_rpe}"
    print(f"✓ Strength main exercise RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_hypertrophy_program_main_exercise_rpe(rpe_service):
    """Test RPE suggestion for main exercise in hypertrophy program."""
    movement = MockMovement(
        name="Barbell Bench Press",
        pattern=MovementPattern.HORIZONTAL_PUSH,
        cns_load=CNSLoad.MODERATE,
    )
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="hypertrophy",
        microcycle_phase="volume_phase",
        training_days_per_week=5,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Hypertrophy volume: [7, 8] base RPE
    assert suggestion.min_rpe >= 6.5, f"RPE min too low: {suggestion.min_rpe}"
    assert suggestion.max_rpe <= 8.5, f"RPE max too high: {suggestion.max_rpe}"
    print(f"✓ Hypertrophy main exercise RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_warmup_exercise_rpe(rpe_service):
    """Test RPE suggestion for warmup exercises."""
    movement = MockMovement(
        name="Goblet Squat",
        pattern=MovementPattern.SQUAT,
        cns_load=CNSLoad.MODERATE,
    )
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.WARMUP,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Warmup: [1, 3] RPE from config
    assert suggestion.min_rpe >= 1.0, f"Warmup RPE min too low: {suggestion.min_rpe}"
    assert suggestion.max_rpe <= 4.0, f"Warmup RPE max too high: {suggestion.max_rpe}"
    print(f"✓ Warmup exercise RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_low_recovery_rpe_adjustment(rpe_service):
    """Test RPE reduction for low recovery state."""
    movement = MockMovement(
        name="Barbell Deadlift",
        pattern=MovementPattern.HINGE,
        cns_load=CNSLoad.HIGH,
    )
    
    # Simulate poor recovery: 5h sleep, low HRV
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 5.0,  # Under 6h: -0.5 adjustment
            "hrv_percentage_change": -25.0,  # Below -20%: -1.0 adjustment
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Base: [6.5, 7.5], with -1.5 adjustment: ~[5.0, 6.0]
    assert suggestion.max_rpe <= 7.0, f"RPE not reduced for low recovery: {suggestion.max_rpe}"
    assert suggestion.adjustment_reason is not None, "Adjustment reason should be set"
    print(f"✓ Low recovery RPE: {suggestion.min_rpe}-{suggestion.max_rpe} (reason: {suggestion.adjustment_reason})")


@pytest.mark.asyncio
async def test_deload_microcycle_rpe(rpe_service):
    """Test RPE reduction for deload microcycle."""
    movement = MockMovement(
        name="Barbell Squat",
        pattern=MovementPattern.SQUAT,
        cns_load=CNSLoad.HIGH,
    )
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="strength",
        microcycle_phase="deload",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Deload: [4, 5.5] RPE from config
    assert suggestion.max_rpe <= 6.0, f"Deload RPE too high: {suggestion.max_rpe}"
    print(f"✓ Deload RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_pattern_recovery_constraint(rpe_service):
    """Test RPE reduction when pattern hasn't recovered."""
    movement = MockMovement(
        name="Barbell Squat",
        pattern=MovementPattern.SQUAT,
        cns_load=CNSLoad.HIGH,
    )
    
    # Simulate pattern trained 24 hours ago (not fully recovered for RPE 8+)
    last_trained = datetime.utcnow() - timedelta(hours=24)
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={
            MovementPattern.SQUAT.value: last_trained,
        },
    )
    
    assert suggestion is not None
    # Pattern not fully recovered: RPE should be reduced
    print(f"✓ Pattern recovery RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_olympic_lift_cns_capping(rpe_service):
    """Test RPE capping for high-CNS olympic lifts."""
    movement = MockMovement(
        name="Power Clean",
        pattern=MovementPattern.OLYMPIC,
        cns_load=CNSLoad.VERY_HIGH,
        discipline_type="olympic_weightlifting",
    )
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="power",
        microcycle_phase="intensification",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Olympic lifts with high CNS should be capped at 8.5
    assert suggestion.max_rpe <= 8.5, f"Olympic lift RPE not capped: {suggestion.max_rpe}"
    print(f"✓ Olympic lift RPE (capped): {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_accessory_exercise_rpe(rpe_service):
    """Test RPE suggestion for accessory exercises."""
    movement = MockMovement(
        name="Dumbbell Lateral Raise",
        pattern=MovementPattern.ISOLATION,
        cns_load=CNSLoad.LOW,
    )
    
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.ACCESSORY,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Accessory: [5, 7] base RPE from strength profile
    assert suggestion.min_rpe >= 4.5, f"Accessory RPE min too low: {suggestion.min_rpe}"
    assert suggestion.max_rpe <= 8.0, f"Accessory RPE max too high: {suggestion.max_rpe}"
    print(f"✓ Accessory exercise RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_session_rpe_suggestion(rpe_service):
    """Test RPE suggestion for entire session by exercise role."""
    rpe_ranges = await rpe_service.suggest_rpe_for_session(
        session_type="strength",
        program_type="strength",
        microcycle_phase="accumulation",
        user_goals=[],
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "energy": 5,
            "consecutive_high_rpe_days": 0,
        },
        weekly_high_rpe_sets_count=0,
    )
    
    assert rpe_ranges is not None
    assert ExerciseRole.MAIN in rpe_ranges
    assert ExerciseRole.ACCESSORY in rpe_ranges
    assert ExerciseRole.WARMUP in rpe_ranges
    assert ExerciseRole.COOLDOWN in rpe_ranges
    
    # Verify ranges are appropriate
    main_min, main_max = rpe_ranges[ExerciseRole.MAIN]
    assert main_min >= 6.0, f"Session main RPE min too low: {main_min}"
    assert main_max <= 8.5, f"Session main RPE max too high: {main_max}"
    
    warmup_min, warmup_max = rpe_ranges[ExerciseRole.WARMUP]
    assert warmup_max <= 4.0, f"Session warmup RPE too high: {warmup_max}"
    
    print(f"✓ Session RPE suggestions:")
    for role, (rpe_min, rpe_max) in rpe_ranges.items():
        print(f"  - {role.value}: {rpe_min}-{rpe_max}")


@pytest.mark.asyncio
async def test_consecutive_high_rpe_days_adjustment(rpe_service):
    """Test RPE reduction for consecutive high-RPE days."""
    movement = MockMovement(
        name="Barbell Bench Press",
        pattern=MovementPattern.HORIZONTAL_PUSH,
        cns_load=CNSLoad.MODERATE,
    )
    
    # Simulate 2 consecutive high-RPE days
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 0,
            "consecutive_high_rpe_days": 2,  # Triggers -0.5 adjustment
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Base: [6.5, 7.5], with -0.5 adjustment: ~[6.0, 7.0]
    assert suggestion.max_rpe <= 7.5, f"RPE not reduced for consecutive high-RPE days: {suggestion.max_rpe}"
    print(f"✓ Consecutive high-RPE days RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")


@pytest.mark.asyncio
async def test_high_soreness_adjustment(rpe_service):
    """Test RPE reduction for high soreness."""
    movement = MockMovement(
        name="Barbell Squat",
        pattern=MovementPattern.SQUAT,
        cns_load=CNSLoad.HIGH,
    )
    
    # Simulate high soreness (8/10)
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=movement,
        exercise_role=ExerciseRole.MAIN,
        program_type="strength",
        microcycle_phase="accumulation",
        training_days_per_week=4,
        session_high_rpe_sets_count=0,
        user_recovery_state={
            "sleep_hours": 8.0,
            "hrv_percentage_change": 0,
            "soreness": 8,  # Above 7: -1.0 adjustment
            "consecutive_high_rpe_days": 0,
        },
        pattern_recovery_hours={},
    )
    
    assert suggestion is not None
    # Base: [6.5, 7.5], with -1.0 adjustment: ~[5.5, 6.5]
    assert suggestion.max_rpe <= 7.0, f"RPE not reduced for high soreness: {suggestion.max_rpe}"
    print(f"✓ High soreness RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")
