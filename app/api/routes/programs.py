"""API routes for program management."""
from datetime import date
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.config import activity_distribution as activity_distribution_config
from app.config.settings import get_settings
from app.models import (
    Program,
    Microcycle,
    Session,
    User,
    UserProfile,
    UserMovementRule,
    UserEnjoyableActivity,
    MicrocycleStatus,
    EnjoyableActivity,
    SessionExercise,
    GenerationStatus,
)
from app.schemas.program import (
    ProgramCreate,
    ProgramResponse,
    ProgramWithSessionsResponse,
    MicrocycleResponse,
    MicrocycleWithSessionsResponse,
    SessionResponse,
    ProgramWithMicrocycleResponse,
    ProgramUpdate,
    ProgramGenerationStatusResponse,
)
from app.services.program import program_service, ProgramService
from app.services.time_estimation import time_estimation_service
from app.api.routes.dependencies import get_current_user_id
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


async def _background_generate_structure(program_id: int):
    """
    Wrapper for background structure generation with comprehensive logging.
    
    Generates microcycles and session shells asynchronously, then triggers
    sequential session content generation.
    """
    logger.info(f"[BACKGROUND_TASK] STARTED structure generation - program_id={program_id}")
    try:
        result = await program_service.generate_program_structure_async(program_id)
        logger.info(
            f"[BACKGROUND_TASK] COMPLETED structure generation - program_id={program_id}, "
            f"status={result.get('status')}"
        )
        
        # After structure is complete, trigger session content generation
        if result.get("status") == "completed":
            logger.info(f"[BACKGROUND_TASK] Triggering session generation - program_id={program_id}")
            await _background_generate_sessions(program_id)
        
        return result
    except Exception as e:
        logger.error(f"[BACKGROUND_TASK] FAILED structure generation - program_id={program_id}, error={e}")
        logger.error(f"[BACKGROUND_TASK] Traceback:\n{traceback.format_exc()}")
        raise


async def _background_generate_sessions(program_id: int):
    """
    Wrapper for background generation with comprehensive logging.
    
    This function wraps program_service.generate_active_microcycle_sessions()
    to ensure all errors are logged and the task lifecycle is tracked.
    """
    logger.info(f"[BACKGROUND_TASK] STARTED session generation - program_id={program_id}")
    try:
        result = await program_service.generate_active_microcycle_sessions(program_id)
        logger.info(
            f"[BACKGROUND_TASK] COMPLETED session generation - program_id={program_id}, "
            f"status={result.get('status')}, "
            f"completed={result.get('completed_sessions')}, "
            f"failed={result.get('failed_sessions')}"
        )
        return result
    except Exception as e:
        logger.error(f"[BACKGROUND_TASK] FAILED session generation - program_id={program_id}, error={e}")
        logger.error(f"[BACKGROUND_TASK] Traceback:\n{traceback.format_exc()}")
        raise


def _normalize_enjoyable_activity(activity_type: str, custom_name: str | None) -> tuple[EnjoyableActivity, str | None]:
    if not activity_type:
        return EnjoyableActivity.OTHER, custom_name
    if activity_type == "custom":
        return EnjoyableActivity.OTHER, custom_name or "custom"
    try:
        return EnjoyableActivity(activity_type), custom_name
    except ValueError:
        return EnjoyableActivity.OTHER, custom_name or activity_type


@router.post("", response_model=ProgramWithMicrocycleResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    program_data: ProgramCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a new training program with immediate skeleton response.
    
    Returns immediately with skeleton structure (microcycles and session shells),
    then starts background generation sequentially for session content.
    
    Requires:
    - 1-3 goals with weights summing to 10
    - Duration of 8-12 weeks
    - Split template selection
    - Progression style selection
    
    Optional:
    - Name (for historic tracking)
    - Persona overrides
    - Movement rules
    - Enjoyable activities
    """
    logger.info("Starting program creation for user_id=%s, data=%s", user_id, program_data.model_dump())
    
    try:
        logger.info("Fetching user with id=%s", user_id)
        user = await db.get(User, user_id)
        logger.info("User fetched: %s", user)
        if not user:
            logger.error("User not found for user_id=%s", user_id)
            raise NotFoundError("User", details={"user_id": user_id})
    except Exception as e:
        logger.exception("Error fetching user: %s", e)
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")
    
    logger.info("Calling ProgramService.create_program_skeleton")
    service = ProgramService(db)
    program = await service.create_program_skeleton(user_id, program_data)
    logger.info("[POST] Program skeleton created successfully with id=%s", program.id)
    
    # Refresh program to load program_disciplines relationship
    logger.info("[POST] Refreshing program with id=%s", program.id)
    await db.refresh(program)
    logger.info("[POST] Program refreshed successfully")
    
    # Explicitly load program_disciplines relationship
    logger.info("[POST] Loading program_disciplines for program_id=%s", program.id)
    result = await db.execute(
        select(Program)
        .options(selectinload(Program.program_disciplines))
        .where(Program.id == program.id)
    )
    program = result.scalar_one()
    logger.info("[POST] Program disciplines loaded successfully")
    
    # Create movement rules if provided (post-program creation)
    if program_data.movement_rules:
        for rule in program_data.movement_rules:
            user_rule = UserMovementRule(
                user_id=user_id,
                movement_id=rule.movement_id,
                rule_type=rule.rule_type,
                cadence=rule.cadence,
                notes=rule.notes,
            )
            db.add(user_rule)
    
    # Create enjoyable activities if provided
    if program_data.enjoyable_activities:
        for activity in program_data.enjoyable_activities:
            activity_enum, normalized_custom_name = _normalize_enjoyable_activity(
                activity.activity_type,
                activity.custom_name,
            )
            user_activity = UserEnjoyableActivity(
                user_id=user_id,
                activity_type=activity_enum,
                custom_name=normalized_custom_name,
                recommend_every_days=activity.recommend_every_days,
                enabled=True,
            )
            db.add(user_activity)
    
    if program_data.movement_rules or program_data.enjoyable_activities:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Unhandled error while saving program preferences")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Schedule background tasks: structure generation, then session generation
    logger.info("[BACKGROUND_TASK] SCHEDULING structure generation for program_id=%s", program.id)
    background_tasks.add_task(_background_generate_structure, program.id)
    logger.info("[BACKGROUND_TASK] SCHEDULED structure generation for program_id=%s", program.id)

    try:
        logger.info("[POST] Validating program for response serialization, program.id=%s", program.id)
        program_response = ProgramResponse.model_validate(program)
        logger.info("[POST] Program validated successfully")

        # Return ProgramWithMicrocycleResponse with empty skeleton
        # Microcycles and sessions will be populated via background task
        response = ProgramWithMicrocycleResponse(
            program=program_response,
            active_microcycle=None,
            upcoming_sessions=[],
            microcycles=[],
        )
        logger.info("[POST] ProgramWithMicrocycleResponse constructed successfully, returning")
        return response
    except Exception as e:
        logger.exception("[POST] Error serializing program response: %s", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error serializing program: {str(e)}")


@router.get("/{program_id}/generation-status", response_model=ProgramGenerationStatusResponse)
async def get_program_generation_status(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get program generation progress status.
    
    Returns microcycle counts by status and the current session/microcycle being generated.
    Useful for frontend polling during background program generation.
    """
    try:
        # Verify program exists and user has access
        result = await db.execute(
            select(Program).where(Program.id == program_id)
        )
        program = result.scalar_one_or_none()

        if not program:
            raise NotFoundError("Program", details={"program_id": program_id})

        if program.user_id != user_id:
            raise AuthorizationError("Not authorized to view this program", details={"program_id": program_id, "user_id": user_id})
    except Exception as e:
        logger.exception("Error fetching program %s: %s", program_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    
    # Count microcycles by status
    try:
        microcycle_counts = await db.execute(
            select(
                Microcycle.status,
                func.count(Microcycle.id).label("count")
            )
            .where(Microcycle.program_id == program_id)
            .group_by(Microcycle.status)
        )
        
        # Initialize counts
        total_microcycles = 0
        completed_microcycles = 0
        in_progress_microcycles = 0
        pending_microcycles = 0
        
        for status, count in microcycle_counts:
            total_microcycles += count
            if status == MicrocycleStatus.COMPLETE:
                completed_microcycles = count
            elif status == MicrocycleStatus.ACTIVE:
                in_progress_microcycles = count
            elif status == MicrocycleStatus.PLANNED:
                pending_microcycles = count
    except Exception as e:
        logger.exception("Error counting microcycles for program %s: %s", program_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    
    # Get current active microcycle
    current_microcycle_id = None
    try:
        active_microcycle = await db.scalar(
            select(Microcycle.id)
            .where(
                and_(
                    Microcycle.program_id == program_id,
                    Microcycle.status == MicrocycleStatus.ACTIVE
                )
            )
        )
        current_microcycle_id = active_microcycle
    except Exception as e:
        logger.exception("Error fetching active microcycle for program %s: %s", program_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    
    # Get current session being generated (with IN_PROGRESS generation_status)
    current_session_id = None
    try:
        session_in_progress = await db.scalar(
            select(Session.id)
            .where(
                and_(
                    Session.microcycle_id == current_microcycle_id if current_microcycle_id else False,
                    Session.generation_status == GenerationStatus.IN_PROGRESS
                )
            )
            .order_by(Session.date)
        )
        current_session_id = session_in_progress
    except Exception as e:
        logger.exception("Error fetching session in progress for program %s: %s", program_id, e)
        # Don't raise error for this - just return None for current_session_id
        current_session_id = None
    
    return ProgramGenerationStatusResponse(
        program_id=program_id,
        total_microcycles=total_microcycles,
        completed_microcycles=completed_microcycles,
        in_progress_microcycles=in_progress_microcycles,
        pending_microcycles=pending_microcycles,
        current_session_id=current_session_id,
        current_microcycle_id=current_microcycle_id,
    )


@router.get("/{program_id}", response_model=ProgramWithMicrocycleResponse)
async def get_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get program with active microcycle, upcoming sessions, and per-week sessions."""
    print(f"DEBUG: get_program called with program_id={program_id}, user_id={user_id}")
    try:
        result = await db.execute(
            select(Program)
            .options(selectinload(Program.program_disciplines))
            .where(Program.id == program_id)
        )
        program = result.scalar_one_or_none()

        if not program:
            raise NotFoundError("Program", details={"program_id": program_id})

        if program.user_id != user_id:
            raise AuthorizationError("Not authorized to view this program", details={"program_id": program_id, "user_id": user_id})
    except Exception as e:
        logger.exception("Error fetching program %s: %s", program_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    
    # Get active microcycle
    try:
        active_microcycle_result = await db.execute(
            select(Microcycle)
            .where(
                and_(
                    Microcycle.program_id == program_id,
                    Microcycle.status == MicrocycleStatus.ACTIVE
                )
            )
            .options(
                selectinload(Microcycle.sessions)
                .options(
                    selectinload(Session.exercises).selectinload(SessionExercise.movement),
                    selectinload(Session.main_circuit),
                    selectinload(Session.finisher_circuit)
                )
            )
        )
        active_microcycle = active_microcycle_result.scalar_one_or_none()
    except Exception as e:
        logger.exception("Error fetching active microcycle for program %s: %s", program_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e

    # Get all microcycles with their sessions
    try:
        microcycles_result = await db.execute(
            select(Microcycle)
            .where(Microcycle.program_id == program_id)
            .options(
                selectinload(Microcycle.sessions)
                .options(
                    selectinload(Session.exercises).selectinload(SessionExercise.movement),
                    selectinload(Session.main_circuit),
                    selectinload(Session.finisher_circuit)
                )
            )
            .order_by(Microcycle.sequence_number)
        )
        microcycles = list(microcycles_result.scalars().unique().all())
    except Exception as e:
        logger.exception("Error fetching microcycles for program %s: %s", program_id, e)
        raise HTTPException(status_code=500, detail="Internal server error") from e

    # Get upcoming sessions (rest of active microcycle)
    upcoming_sessions = []
    print(f"DEBUG: active_microcycle = {active_microcycle}")
    if active_microcycle:
        today = date.today()
        from datetime import timedelta
        microcycle_end = active_microcycle.start_date + timedelta(days=active_microcycle.length_days)
        logger.debug("Fetching sessions from %s to %s", today, microcycle_end)
        try:
            sessions_result = await db.execute(
                select(Session)
                .where(
                    and_(
                        Session.microcycle_id == active_microcycle.id,
                        Session.date >= today,
                        Session.date < microcycle_end,
                    )
                )
                .options(
                    selectinload(Session.exercises).selectinload(SessionExercise.movement),
                    selectinload(Session.main_circuit),
                    selectinload(Session.finisher_circuit)
                )
                .order_by(Session.date)
            )
            upcoming_sessions = list(sessions_result.scalars().all())
            print(f"DEBUG: Found {len(upcoming_sessions)} upcoming sessions")
        except Exception as e:
            logger.exception("Error fetching upcoming sessions for microcycle %s: %s", active_microcycle.id, e)
            raise HTTPException(status_code=500, detail="Internal server error") from e
    
    # Convert upcoming sessions to response format with duration estimates
    # Use simple estimation to avoid N+1 query problem
    session_responses = []
    for session in upcoming_sessions:
        if not session.estimated_duration_minutes:
            try:
                breakdown = time_estimation_service.calculate_session_duration(session)
                session.estimated_duration_minutes = breakdown.total_minutes
                session.warmup_duration_minutes = breakdown.warmup_minutes
                session.main_duration_minutes = breakdown.main_minutes
                session.accessory_duration_minutes = breakdown.accessory_minutes
                session.finisher_duration_minutes = breakdown.finisher_minutes
                session.cooldown_duration_minutes = breakdown.cooldown_minutes
            except Exception as e:
                logger.warning("Error calculating duration for session %s: %s", session.id, e)
                # Simple estimation: 4 mins per exercise + 10 mins warmup
                exercise_count = len(session.exercises) if session.exercises else 0
                session.estimated_duration_minutes = 10 + (exercise_count * 4)
        
        try:
            print(f"DEBUG: Validating session {session.id}")
            session_responses.append(SessionResponse.model_validate(session))
        except Exception as e:
            print(f"ERROR validating session {session.id}: {e}")
            import traceback
            traceback.print_exc()
            logger.exception("Error validating session %s to response model: %s", session.id, e)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    # Build per-microcycle session views
    microcycle_responses: list[MicrocycleWithSessionsResponse] = []
    logger.debug("Processing %d microcycles", len(microcycles))
    for microcycle in microcycles:
        microcycle_sessions: list[SessionResponse] = []
        # Ensure sessions are ordered by day_number
        ordered_sessions = sorted(
                microcycle.sessions or [],
                key=lambda s: (s.day_number, s.date or date.min),
            )
        logger.debug("Microcycle %s has %d sessions", microcycle.id, len(ordered_sessions))
        for session in ordered_sessions:
            if not session.estimated_duration_minutes:
                try:
                    # Attempt calculation if not set
                    breakdown = time_estimation_service.calculate_session_duration(session)
                    session.estimated_duration_minutes = breakdown.total_minutes
                except Exception as e:
                    logger.warning("Error calculating duration for microcycle session %s: %s", session.id, e)
                    # Simple estimation: 4 mins per exercise + 10 mins warmup
                    exercise_count = len(session.exercises) if session.exercises else 0
                    session.estimated_duration_minutes = 10 + (exercise_count * 4)

            try:
                logger.debug("Validating microcycle session %s", session.id)
                microcycle_sessions.append(SessionResponse.model_validate(session))
            except Exception as e:
                logger.exception("Error validating microcycle session %s to response model: %s", session.id, e)
                raise HTTPException(status_code=500, detail="Internal server error") from e

        microcycle_responses.append(
            MicrocycleWithSessionsResponse(
                id=microcycle.id,
                program_id=microcycle.program_id,
                micro_start_date=microcycle.start_date,
                length_days=microcycle.length_days,
                sequence_number=microcycle.sequence_number,
                status=microcycle.status,
                is_deload=microcycle.is_deload,
                generation_status=microcycle.generation_status,
                sessions=microcycle_sessions,
            )
        )

    print("DEBUG: Constructing ProgramWithMicrocycleResponse")
    print(f"DEBUG: program={program}, active_microcycle={active_microcycle}")
    print(f"DEBUG: upcoming_sessions count={len(session_responses)}, microcycles count={len(microcycle_responses)}")
    
    try:
        response = ProgramWithMicrocycleResponse(
            program=program,
            active_microcycle=active_microcycle,
            upcoming_sessions=session_responses,
            microcycles=microcycle_responses,
        )
        logger.debug("ProgramWithMicrocycleResponse constructed successfully")
        return response
    except Exception as e:
        logger.exception("Error constructing ProgramWithMicrocycleResponse: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("", response_model=list[ProgramWithSessionsResponse])
async def list_programs(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List all programs for the current user. Includes session data for active programs."""
    logger.info("list_programs called: user_id=%s, active_only=%s", user_id, active_only)
    
    query = select(Program).options(selectinload(Program.program_disciplines)).where(Program.user_id == user_id)
    
    if active_only:
        query = query.where(Program.is_active.is_(True))
    
    query = query.order_by(Program.is_active.desc(), Program.created_at.desc())
    
    result = await db.execute(query)
    programs = list(result.scalars().unique().all())
    
    logger.info("list_programs: found %d programs for user_id=%s", len(programs), user_id)
    
    # For active programs, load upcoming sessions
    programs_with_sessions = []
    for prog in programs:
        logger.info("  Program id=%s, name=%s, is_active=%s, created_at=%s", prog.id, prog.name, prog.is_active, prog.created_at)
        
        upcoming_sessions = []
        if prog.is_active:
            try:
                # Get active microcycle for this program
                active_microcycle_result = await db.execute(
                    select(Microcycle)
                    .where(
                        and_(
                            Microcycle.program_id == prog.id,
                            Microcycle.status == MicrocycleStatus.ACTIVE
                        )
                    )
                )
                active_microcycle = active_microcycle_result.scalar_one_or_none()
                
                if active_microcycle:
                    today = date.today()
                    from datetime import timedelta
                    microcycle_end = active_microcycle.start_date + timedelta(days=active_microcycle.length_days)
                    
                    # Fetch upcoming sessions from today to end of active microcycle
                    sessions_result = await db.execute(
                        select(Session)
                        .where(
                            and_(
                                Session.microcycle_id == active_microcycle.id,
                                Session.date >= today,
                                Session.date < microcycle_end,
                            )
                        )
                        .options(
                            selectinload(Session.exercises).selectinload(SessionExercise.movement),
                            selectinload(Session.main_circuit),
                            selectinload(Session.finisher_circuit)
                        )
                        .order_by(Session.date)
                    )
                    sessions = list(sessions_result.scalars().all())
                    
                    # Calculate duration estimates and convert to response format
                    for session in sessions:
                        if not session.estimated_duration_minutes:
                            try:
                                breakdown = time_estimation_service.calculate_session_duration(session)
                                session.estimated_duration_minutes = breakdown.total_minutes
                                session.warmup_duration_minutes = breakdown.warmup_minutes
                                session.main_duration_minutes = breakdown.main_minutes
                                session.accessory_duration_minutes = breakdown.accessory_minutes
                                session.finisher_duration_minutes = breakdown.finisher_minutes
                                session.cooldown_duration_minutes = breakdown.cooldown_minutes
                            except Exception as e:
                                logger.warning("Error calculating duration for session %s: %s", session.id, e)
                                exercise_count = len(session.exercises) if session.exercises else 0
                                session.estimated_duration_minutes = 10 + (exercise_count * 4)
                        
                        try:
                            upcoming_sessions.append(SessionResponse.model_validate(session))
                        except Exception as e:
                            logger.exception("Error validating session %s to response model: %s", session.id, e)
                    
                    logger.info("    Loaded %d upcoming sessions for active program", len(upcoming_sessions))
            except Exception as e:
                logger.exception("Error fetching sessions for program %s: %s", prog.id, e)
        
        # Create ProgramWithSessionsResponse
        program_data = {
            "id": prog.id,
            "user_id": prog.user_id,
            "name": prog.name,
            "program_start_date": prog.start_date,
            "duration_weeks": prog.duration_weeks,
            "days_per_week": prog.days_per_week,
            "max_session_duration": prog.max_session_duration,
            "goal_1": prog.goal_1,
            "goal_2": prog.goal_2,
            "goal_3": prog.goal_3,
            "goal_weight_1": prog.goal_weight_1,
            "goal_weight_2": prog.goal_weight_2,
            "goal_weight_3": prog.goal_weight_3,
            "split_template": prog.split_template,
            "progression_style": prog.progression_style,
            "hybrid_definition": prog.hybrid_definition,
            "deload_every_n_microcycles": prog.deload_every_n_microcycles,
            "persona_tone": prog.persona_tone,
            "persona_aggression": prog.persona_aggression,
            "is_active": prog.is_active,
            "created_at": prog.created_at,
            "program_disciplines": [
                {"discipline": pd.discipline, "weight": pd.weight}
                for pd in prog.program_disciplines
            ],
            "upcoming_sessions": upcoming_sessions
        }
        
        programs_with_sessions.append(ProgramWithSessionsResponse(**program_data))
    
    return programs_with_sessions


@router.post("/{program_id}/microcycles/generate-next", response_model=MicrocycleResponse)
async def generate_next_microcycle(
    program_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Generate the next microcycle for a program.
    
    This will:
    1. Mark the current active microcycle as complete
    2. Create a new microcycle
    3. Generate sessions for the new microcycle using LLM
    """
    program = await db.get(Program, program_id)

    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})

    if program.user_id != user_id:
        raise AuthorizationError("Not authorized", details={"program_id": program_id, "user_id": user_id})
    
    # Get current active microcycle
    active_result = await db.execute(
        select(Microcycle)
        .where(
            and_(
                Microcycle.program_id == program_id,
                Microcycle.status == MicrocycleStatus.ACTIVE
            )
        )
    )
    current_microcycle = active_result.scalar_one_or_none()
    
    # Determine sequence number and start date
    if current_microcycle:
        current_microcycle.status = MicrocycleStatus.COMPLETE
        next_seq = current_microcycle.sequence_number + 1
        next_start = current_microcycle.start_date
        # Add current microcycle length
        from datetime import timedelta
        next_start = next_start + timedelta(days=current_microcycle.length_days)
    else:
        next_seq = 1
        next_start = program.start_date
    
    # Determine if this is a deload week
    is_deload = (next_seq % program.deload_every_n_microcycles == 0)

    user_profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    scheduling_prefs = user_profile.scheduling_preferences if user_profile else {}
    pref_length = (scheduling_prefs or {}).get("microcycle_length_days")
    if isinstance(pref_length, int) and 7 <= pref_length <= 14:
        length_days = pref_length
    else:
        length_days = activity_distribution_config.default_microcycle_length_days
    
    # Create new microcycle
    new_microcycle = Microcycle(
        program_id=program_id,
        start_date=next_start,
        length_days=length_days,
        sequence_number=next_seq,
        status=MicrocycleStatus.ACTIVE,
        is_deload=is_deload,
    )
    db.add(new_microcycle)
    
    await db.commit()
    await db.refresh(new_microcycle)
    
    # Generate sessions in background with comprehensive logging
    logger.info("[BACKGROUND_TASK] SCHEDULING generation for next microcycle, program_id=%s", program_id)
    background_tasks.add_task(_background_generate_sessions, program_id)
    logger.info("[BACKGROUND_TASK] SCHEDULED generation for next microcycle, program_id=%s", program_id)
    
    return new_microcycle


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a program."""
    program = await db.get(Program, program_id)

    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})

    if program.user_id != user_id:
        raise AuthorizationError("Not authorized", details={"program_id": program_id, "user_id": user_id})
    
    await db.delete(program)
    await db.commit()


@router.patch("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: int,
    program_update: ProgramUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update program details (name, status)."""
    program = await db.get(Program, program_id)
    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})
    if program.user_id != user_id:
        raise AuthorizationError("Not authorized", details={"program_id": program_id, "user_id": user_id})
    
    update_data = program_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(program, field, value)
    
    await db.commit()
    await db.refresh(program)
    return program


@router.post("/{program_id}/activate", response_model=ProgramResponse)
async def activate_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Activate a program (deactivates any other active programs)."""
    program = await db.get(Program, program_id)

    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})

    if program.user_id != user_id:
        raise AuthorizationError("Not authorized", details={"program_id": program_id, "user_id": user_id})
    
    # Deactivate other programs
    other_active = await db.execute(
        select(Program).where(
            and_(
                Program.user_id == user_id,
                Program.is_active.is_(True),
                Program.id != program_id
            )
        )
    )
    for prog in other_active.scalars():
        prog.is_active = False
    
    program.is_active = True
    await db.commit()
    await db.refresh(program, ['program_disciplines'])
    
    return program
