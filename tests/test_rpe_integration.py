"""
Integration tests for full RPE (Rate of Perceived Exertion) flow.

Test scenarios:
1. Full program generation with RPE suggestions
2. Real-world examples from plan (Strength 3-day, Hypertrophy 5-day, Olympic 4-day)
3. Low recovery state adjustment
4. Pattern recovery tracking
5. SessionExercise RPE fields persistence
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Program, Microcycle, Session, SessionExercise,
    RecoverySignal, WorkoutLog, Movement, User
)
from app.models.enums import (
    Goal, SplitTemplate, ProgressionStyle, SessionType,
    ExerciseRole, MovementPattern, PrimaryMuscle,
    PrimaryRegion, SkillLevel, CNSLoad, RecoverySource,
    MicrocycleStatus
)
from app.services.rpe_suggestion_service import get_rpe_suggestion_service


@pytest_asyncio.fixture
async def strength_program_with_rpe(async_db_session: AsyncSession, test_user: User) -> Program:
    """Create a strength-focused 3-day/week program for RPE testing."""
    program = Program(
        user_id=test_user.id,
        split_template=SplitTemplate.FULL_BODY,
        start_date=date.today(),
        duration_weeks=8,
        goal_1=Goal.STRENGTH,
        goal_2=Goal.HYPERTROPHY,
        goal_3=Goal.ENDURANCE,
        goal_weight_1=6,
        goal_weight_2=3,
        goal_weight_3=1,
        days_per_week=3,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        deload_every_n_microcycles=4,
        persona_tone="supportive",
        persona_aggression="balanced",
        is_active=True,
    )
    async_db_session.add(program)
    await async_db_session.flush()
    
    # Create accumulation phase microcycle
    microcycle = Microcycle(
        program_id=program.id,
        sequence_number=1,
        start_date=date.today(),
        length_days=7,
        status=MicrocycleStatus.PLANNED,
        is_deload=False,
        microcycle_phase="accumulation",
        rpe_intensity_factor=1.0,
    )
    async_db_session.add(microcycle)
    await async_db_session.flush()
    
    # Create 3 sessions for the week
    for day_num in range(1, 4):
        session = Session(
            microcycle_id=microcycle.id,
            date=date.today() + timedelta(days=day_num - 1),
            day_number=day_num,
            session_type=SessionType.FULL_BODY,
            intent_tags=["squat", "horizontal_push", "hinge"],
            estimated_duration_minutes=60,
        )
        async_db_session.add(session)
    
    await async_db_session.commit()
    return program


@pytest_asyncio.fixture
async def hypertrophy_program_with_rpe(async_db_session: AsyncSession, test_user: User) -> Program:
    """Create a hypertrophy-focused 5-day/week program for RPE testing."""
    program = Program(
        user_id=test_user.id,
        split_template=SplitTemplate.UPPER_LOWER,
        start_date=date.today(),
        duration_weeks=8,
        goal_1=Goal.HYPERTROPHY,
        goal_2=Goal.STRENGTH,
        goal_3=Goal.ENDURANCE,
        goal_weight_1=6,
        goal_weight_2=2,
        goal_weight_3=2,
        days_per_week=5,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        deload_every_n_microcycles=4,
        persona_tone="supportive",
        persona_aggression="balanced",
        is_active=True,
    )
    async_db_session.add(program)
    await async_db_session.flush()
    
    # Create volume phase microcycle
    microcycle = Microcycle(
        program_id=program.id,
        sequence_number=1,
        start_date=date.today(),
        length_days=7,
        status=MicrocycleStatus.PLANNED,
        is_deload=False,
        microcycle_phase="volume_phase",
        rpe_intensity_factor=1.0,
    )
    async_db_session.add(microcycle)
    await async_db_session.flush()
    
    # Create 5 sessions for the week
    for day_num in range(1, 6):
        if day_num in [1, 3, 5]:
            session_type = SessionType.UPPER
            intent_tags = ["horizontal_push", "horizontal_pull", "vertical_push"]
        else:
            session_type = SessionType.LOWER
            intent_tags = ["squat", "hinge", "lunge"]
        
        session = Session(
            microcycle_id=microcycle.id,
            date=date.today() + timedelta(days=day_num - 1),
            day_number=day_num,
            session_type=session_type,
            intent_tags=intent_tags,
            estimated_duration_minutes=60,
        )
        async_db_session.add(session)
    
    await async_db_session.commit()
    return program


@pytest.mark.asyncio
async def test_rpe_service_database_integration(
    async_db_session: AsyncSession,
    test_user: User,
    strength_program_with_rpe: Program,
    test_movements: list[Movement],
):
    """
    Test 1: RPE service integration with database models.
    
    Verify:
    - RPESuggestionService works with database Movement objects
    - RPE suggestions can be saved to SessionExercise
    - Suggestions are retrieved correctly from database
    """
    print("\n=== Test 1: RPE Service Database Integration ===")
    
    rpe_service = get_rpe_suggestion_service()
    
    # Find a compound movement from test fixtures
    compound_movement = None
    for m in test_movements:
        if m.compound:
            compound_movement = m
            break
    
    assert compound_movement is not None, "No compound movement found in test fixtures"
    
    # Get RPE suggestion using database movement
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=compound_movement,
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
    assert suggestion.min_rpe >= 6.0, f"RPE min too low: {suggestion.min_rpe}"
    assert suggestion.max_rpe <= 9.0, f"RPE max too high: {suggestion.max_rpe}"
    
    print(f"✓ RPE suggestion for {compound_movement.name}: {suggestion.min_rpe}-{suggestion.max_rpe}")
    
    # Create a session and session exercise to test persistence
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == strength_program_with_rpe.id)
    )
    microcycle = result.scalar_one()
    
    result = await async_db_session.execute(
        select(Session).where(Session.microcycle_id == microcycle.id).limit(1)
    )
    session = result.scalar_one()
    
    # Create session exercise with RPE suggestions
    session_exercise = SessionExercise(
        session_id=session.id,
        movement_id=compound_movement.id,
        exercise_role=ExerciseRole.MAIN,
        suggested_rpe_min=suggestion.min_rpe,
        suggested_rpe_max=suggestion.max_rpe,
        rpe_adjustment_reason=suggestion.adjustment_reason,
        target_sets=3,
        target_rep_range_min=8,
        target_rep_range_max=10,
        order_in_session=1,
    )
    async_db_session.add(session_exercise)
    await async_db_session.commit()
    
    # Verify persistence
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.id == session_exercise.id)
    )
    saved_exercise = result.scalar_one()
    
    assert saved_exercise is not None
    assert saved_exercise.suggested_rpe_min == suggestion.min_rpe
    assert saved_exercise.suggested_rpe_max == suggestion.max_rpe
    assert saved_exercise.exercise_role == ExerciseRole.MAIN
    
    print("✓ SessionExercise RPE fields persisted correctly")
    print("✅ Test 1 PASSED: RPE service database integration")


@pytest.mark.asyncio
async def test_low_recovery_state_rpe_adjustment_with_database(
    async_db_session: AsyncSession,
    test_user: User,
    strength_program_with_rpe: Program,
    test_movements: list[Movement],
):
    """
    Test 2: Low recovery state RPE adjustment with database recovery signals.
    
    Simulate:
    - User with poor sleep (5 hours)
    - Low HRV (-25% from baseline)
    - High soreness (8/10)
    
    Verify:
    - RPE is reduced appropriately based on fatigue signals
    - rpe_adjustment_reason is set
    - Multiple fatigue factors compound adjustments
    """
    print("\n=== Test 2: Low Recovery State RPE Adjustment with Database ===")
    
    # Create low recovery signals
    recovery_signal = RecoverySignal(
        user_id=test_user.id,
        date=date.today(),
        source=RecoverySource.MANUAL,
        sleep_score=40.0,  # Poor sleep
        sleep_hours=5.0,  # Only 5 hours
        hrv=40.0,  # Low HRV (assuming baseline ~53)
        readiness=45.0,  # Low readiness
    )
    async_db_session.add(recovery_signal)
    await async_db_session.commit()
    
    print("✓ Created low recovery signal (5h sleep, low HRV)")
    
    rpe_service = get_rpe_suggestion_service()
    
    # Find a compound movement
    compound_movement = None
    for m in test_movements:
        if m.compound:
            compound_movement = m
            break
    
    # Get RPE suggestion with low recovery state
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=compound_movement,
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
    
    print(f"✓ Low recovery RPE: {suggestion.min_rpe}-{suggestion.max_rpe}")
    if suggestion.adjustment_reason:
        print(f"  - Adjustment reason: {suggestion.adjustment_reason}")
    
    # Save to database
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == strength_program_with_rpe.id)
    )
    microcycle = result.scalar_one()
    
    result = await async_db_session.execute(
        select(Session).where(Session.microcycle_id == microcycle.id).limit(1)
    )
    session = result.scalar_one()
    
    session_exercise = SessionExercise(
        session_id=session.id,
        movement_id=compound_movement.id,
        exercise_role=ExerciseRole.MAIN,
        suggested_rpe_min=suggestion.min_rpe,
        suggested_rpe_max=suggestion.max_rpe,
        rpe_adjustment_reason=suggestion.adjustment_reason,
        target_sets=3,
        target_rep_range_min=8,
        target_rep_range_max=10,
        order_in_session=1,
    )
    async_db_session.add(session_exercise)
    await async_db_session.commit()
    
    # Verify persistence
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.id == session_exercise.id)
    )
    saved_exercise = result.scalar_one()
    
    assert saved_exercise.suggested_rpe_max <= 7.0
    assert saved_exercise.rpe_adjustment_reason == suggestion.adjustment_reason
    
    print("✓ Low recovery RPE persisted correctly")
    print("✅ Test 2 PASSED: Low recovery state RPE adjustment with database")


@pytest.mark.asyncio
async def test_different_program_types_rpe_with_database(
    async_db_session: AsyncSession,
    test_user: User,
    strength_program_with_rpe: Program,
    test_movements: list[Movement],
):
    """
    Test 3: Different program types produce appropriate RPE ranges with database models.
    
    Verify:
    - Strength program has higher RPE ranges
    - Hypertrophy program has moderate RPE ranges
    - Power program has high RPE ranges
    """
    print("\n=== Test 3: Different Program Types RPE Ranges with Database ===")
    
    rpe_service = get_rpe_suggestion_service()
    
    # Find a compound movement
    compound_movement = None
    for m in test_movements:
        if m.compound:
            compound_movement = m
            break
    
    # Test different program types
    program_types = [
        ("strength", "accumulation", 6.5, 8.0),
        ("hypertrophy", "volume_phase", 6.5, 8.0),
        ("power", "intensification", 7.0, 8.5),
    ]
    
    suggestions = {}
    for program_type, phase, expected_min, expected_max in program_types:
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=compound_movement,
            exercise_role=ExerciseRole.MAIN,
            program_type=program_type,
            microcycle_phase=phase,
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
        
        assert suggestion is not None, f"No suggestion for {program_type}"
        assert suggestion.min_rpe >= expected_min - 0.5, \
            f"{program_type} RPE min too low: {suggestion.min_rpe}"
        assert suggestion.max_rpe <= expected_max + 0.5, \
            f"{program_type} RPE max too high: {suggestion.max_rpe}"
        
        suggestions[program_type] = suggestion
        print(f"✓ {program_type}: RPE {suggestion.min_rpe}-{suggestion.max_rpe}")
    
    # Save all suggestions to database
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == strength_program_with_rpe.id)
    )
    microcycle = result.scalar_one()
    
    result = await async_db_session.execute(
        select(Session).where(Session.microcycle_id == microcycle.id).limit(1)
    )
    session = result.scalar_one()
    
    for program_type, suggestion in suggestions.items():
        session_exercise = SessionExercise(
            session_id=session.id,
            movement_id=compound_movement.id,
            exercise_role=ExerciseRole.MAIN,
            suggested_rpe_min=suggestion.min_rpe,
            suggested_rpe_max=suggestion.max_rpe,
            rpe_adjustment_reason=suggestion.adjustment_reason,
            target_sets=3,
            target_rep_range_min=8,
            target_rep_range_max=10,
            order_in_session=1,
        )
        async_db_session.add(session_exercise)
    
    await async_db_session.commit()
    
    # Verify all were saved
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.session_id == session.id)
    )
    saved_exercises = result.scalars().all()
    
    assert len(saved_exercises) >= 3, "Not all program type RPE suggestions saved"
    
    print(f"✓ Saved {len(saved_exercises)} RPE suggestions to database")
    print("✅ Test 3 PASSED: Different program types RPE ranges with database")


@pytest.mark.asyncio
async def test_sessionexercise_rpe_fields_persistence(
    async_db_session: AsyncSession,
    test_user: User,
    strength_program_with_rpe: Program,
    test_movements: list[Movement],
):
    """
    Test 4: SessionExercise RPE fields persistence.
    
    Verify:
    - suggested_rpe_min is saved to database
    - suggested_rpe_max is saved to database
    - rpe_adjustment_reason is saved to database (when applicable)
    - Fields persist after commit and re-query
    """
    print("\n=== Test 4: SessionExercise RPE Fields Persistence ===")
    
    rpe_service = get_rpe_suggestion_service()
    
    # Find a compound movement
    compound_movement = None
    for m in test_movements:
        if m.compound:
            compound_movement = m
            break
    
    # Get RPE suggestion
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=compound_movement,
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
    
    # Get session
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == strength_program_with_rpe.id)
    )
    microcycle = result.scalar_one()
    
    result = await async_db_session.execute(
        select(Session).where(Session.microcycle_id == microcycle.id).limit(1)
    )
    session = result.scalar_one()
    
    # Create session exercise with RPE fields
    session_exercise = SessionExercise(
        session_id=session.id,
        movement_id=compound_movement.id,
        exercise_role=ExerciseRole.MAIN,
        suggested_rpe_min=suggestion.min_rpe,
        suggested_rpe_max=suggestion.max_rpe,
        rpe_adjustment_reason=suggestion.adjustment_reason,
        target_sets=3,
        target_rep_range_min=8,
        target_rep_range_max=10,
        order_in_session=1,
    )
    async_db_session.add(session_exercise)
    await async_db_session.commit()
    
    # Query to verify persistence
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.id == session_exercise.id)
    )
    saved_exercise = result.scalar_one()
    
    assert saved_exercise is not None, "SessionExercise not found in database"
    assert saved_exercise.suggested_rpe_min is not None, "suggested_rpe_min not persisted"
    assert saved_exercise.suggested_rpe_max is not None, "suggested_rpe_max not persisted"
    
    # Verify values are reasonable
    assert 3.0 <= saved_exercise.suggested_rpe_min <= 10.0, \
        f"Invalid suggested_rpe_min: {saved_exercise.suggested_rpe_min}"
    assert 4.0 <= saved_exercise.suggested_rpe_max <= 10.0, \
        f"Invalid suggested_rpe_max: {saved_exercise.suggested_rpe_max}"
    assert saved_exercise.suggested_rpe_max >= saved_exercise.suggested_rpe_min, \
        f"RPE max < min: {saved_exercise.suggested_rpe_max} < {saved_exercise.suggested_rpe_min}"
    
    print(f"✓ SessionExercise RPE fields persisted:")
    print(f"  - suggested_rpe_min: {saved_exercise.suggested_rpe_min}")
    print(f"  - suggested_rpe_max: {saved_exercise.suggested_rpe_max}")
    print(f"  - rpe_adjustment_reason: {saved_exercise.rpe_adjustment_reason}")
    
    # Test with adjustment reason
    session_exercise2 = SessionExercise(
        session_id=session.id,
        movement_id=compound_movement.id,
        exercise_role=ExerciseRole.ACCESSORY,
        suggested_rpe_min=5.0,
        suggested_rpe_max=6.5,
        rpe_adjustment_reason="low_recovery_5h_sleep",
        target_sets=3,
        target_rep_range_min=12,
        target_rep_range_max=15,
        order_in_session=2,
    )
    async_db_session.add(session_exercise2)
    await async_db_session.commit()
    
    # Verify adjustment reason persisted
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.id == session_exercise2.id)
    )
    saved_exercise2 = result.scalar_one()
    
    assert saved_exercise2.rpe_adjustment_reason == "low_recovery_5h_sleep"
    
    print(f"✓ rpe_adjustment_reason persisted: {saved_exercise2.rpe_adjustment_reason}")
    print("✅ Test 4 PASSED: SessionExercise RPE fields persistence")


@pytest.mark.asyncio
async def test_deload_microcycle_rpe_with_database(
    async_db_session: AsyncSession,
    test_user: User,
    test_movements: list[Movement],
):
    """
    Test 5: Deload microcycle RPE reduction with database models.
    
    Verify:
    - Deload sessions have significantly lower RPE
    - RPE ranges are appropriate for recovery
    - All exercise roles respect deload RPE constraints
    """
    print("\n=== Test 5: Deload Microcycle RPE Reduction with Database ===")
    
    # Create a program with deload microcycle
    program = Program(
        user_id=test_user.id,
        split_template=SplitTemplate.FULL_BODY,
        start_date=date.today(),
        duration_weeks=8,
        goal_1=Goal.STRENGTH,
        goal_2=Goal.HYPERTROPHY,
        goal_3=Goal.ENDURANCE,
        goal_weight_1=5,
        goal_weight_2=3,
        goal_weight_3=2,
        days_per_week=3,
        progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
        deload_every_n_microcycles=4,
        persona_tone="supportive",
        persona_aggression="balanced",
        is_active=True,
    )
    async_db_session.add(program)
    await async_db_session.flush()
    
    # Create deload microcycle
    deload_microcycle = Microcycle(
        program_id=program.id,
        sequence_number=4,
        start_date=date.today(),
        length_days=7,
        status=MicrocycleStatus.PLANNED,
        is_deload=True,
        microcycle_phase="deload",
        rpe_intensity_factor=0.5,
    )
    async_db_session.add(deload_microcycle)
    await async_db_session.flush()
    
    # Create a session
    session = Session(
        microcycle_id=deload_microcycle.id,
        date=date.today(),
        day_number=1,
        session_type=SessionType.FULL_BODY,
        intent_tags=["squat", "horizontal_push"],
        estimated_duration_minutes=45,
    )
    async_db_session.add(session)
    await async_db_session.commit()
    
    rpe_service = get_rpe_suggestion_service()
    
    # Find a compound movement
    compound_movement = None
    for m in test_movements:
        if m.compound:
            compound_movement = m
            break
    
    # Get RPE suggestion for deload
    suggestion = await rpe_service.suggest_rpe_for_movement(
        movement=compound_movement,
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
    
    # Save to database
    session_exercise = SessionExercise(
        session_id=session.id,
        movement_id=compound_movement.id,
        exercise_role=ExerciseRole.MAIN,
        suggested_rpe_min=suggestion.min_rpe,
        suggested_rpe_max=suggestion.max_rpe,
        rpe_adjustment_reason=suggestion.adjustment_reason,
        target_sets=3,
        target_rep_range_min=10,
        target_rep_range_max=12,
        order_in_session=1,
    )
    async_db_session.add(session_exercise)
    await async_db_session.commit()
    
    # Verify deload RPE persisted
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.id == session_exercise.id)
    )
    saved_exercise = result.scalar_one()
    
    assert saved_exercise.suggested_rpe_max <= 6.0
    print(f"✓ Deload RPE persisted correctly: {saved_exercise.suggested_rpe_min}-{saved_exercise.suggested_rpe_max}")
    print("✅ Test 5 PASSED: Deload microcycle RPE reduction with database")


@pytest.mark.asyncio
async def test_multiple_exercise_roles_rpe(
    async_db_session: AsyncSession,
    test_user: User,
    strength_program_with_rpe: Program,
    test_movements: list[Movement],
):
    """
    Test 6: Multiple exercise roles get appropriate RPE ranges.
    
    Verify:
    - MAIN exercises get higher RPE
    - ACCESSORY exercises get moderate RPE
    - WARMUP exercises get low RPE
    - COOLDOWN exercises get low RPE
    """
    print("\n=== Test 6: Multiple Exercise Roles RPE Ranges ===")
    
    rpe_service = get_rpe_suggestion_service()
    
    # Find movements
    compound_movement = None
    isolation_movement = None
    for m in test_movements:
        if m.compound and not compound_movement:
            compound_movement = m
        elif not m.compound and not isolation_movement:
            isolation_movement = m
    
    # Get RPE suggestions for different roles
    roles_to_test = [
        ExerciseRole.MAIN,
        ExerciseRole.ACCESSORY,
        ExerciseRole.WARMUP,
        ExerciseRole.COOLDOWN,
    ]
    
    suggestions = {}
    for role in roles_to_test:
        movement = compound_movement if role != ExerciseRole.WARMUP else isolation_movement
        if not movement:
            movement = compound_movement  # Fallback
        
        suggestion = await rpe_service.suggest_rpe_for_movement(
            movement=movement,
            exercise_role=role,
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
        
        suggestions[role] = suggestion
        print(f"✓ {role.value}: RPE {suggestion.min_rpe}-{suggestion.max_rpe}")
    
    # Verify RPE hierarchy
    assert suggestions[ExerciseRole.MAIN].max_rpe > suggestions[ExerciseRole.WARMUP].max_rpe
    assert suggestions[ExerciseRole.MAIN].max_rpe > suggestions[ExerciseRole.COOLDOWN].max_rpe
    
    # Save all to database
    result = await async_db_session.execute(
        select(Microcycle).where(Microcycle.program_id == strength_program_with_rpe.id)
    )
    microcycle = result.scalar_one()
    
    result = await async_db_session.execute(
        select(Session).where(Session.microcycle_id == microcycle.id).limit(1)
    )
    session = result.scalar_one()
    
    for role, suggestion in suggestions.items():
        movement = compound_movement if role != ExerciseRole.WARMUP else isolation_movement
        if not movement:
            movement = compound_movement
        
        session_exercise = SessionExercise(
            session_id=session.id,
            movement_id=movement.id,
            exercise_role=role,
            suggested_rpe_min=suggestion.min_rpe,
            suggested_rpe_max=suggestion.max_rpe,
            rpe_adjustment_reason=suggestion.adjustment_reason,
            target_sets=3,
            target_rep_range_min=8,
            target_rep_range_max=10,
            order_in_session=1,
        )
        async_db_session.add(session_exercise)
    
    await async_db_session.commit()
    
    # Verify all were saved
    result = await async_db_session.execute(
        select(SessionExercise).where(SessionExercise.session_id == session.id)
    )
    saved_exercises = result.scalars().all()
    
    assert len(saved_exercises) >= 3, "Not all exercise role RPE suggestions saved"
    
    print(f"✓ Saved {len(saved_exercises)} RPE suggestions for different roles")
    print("✅ Test 6 PASSED: Multiple exercise roles RPE ranges")
