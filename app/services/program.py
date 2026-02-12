"""
ProgramService - Generates workout programs with microcycle structure and goal distribution.

Responsible for:
- Creating 8-12 week programs from split template + goal mix
- Distributing goals across microcycles with weighting
- Generating microcycles with appropriate intensity profiles
- Creating session templates with optional sections (warmup, finisher, conditioning)
- Applying movement rule constraints and interference logic
"""

from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import logging
import traceback
import asyncio
from sqlalchemy import select, and_, or_, cast, String
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Program, Microcycle, Session, HeuristicConfig, User, Movement, UserProfile, UserMovementRule, SessionExercise, ProgramDiscipline, MovementDiscipline
)
from app.schemas.program import ProgramCreate
from app.schemas.pagination import PaginationParams
from app.models.enums import (
    Goal, SplitTemplate, SessionType, MicrocycleStatus, PersonaTone, PersonaAggression,
    ProgressionStyle, MovementRuleType, ExerciseRole, GenerationStatus, DisciplineType
)
from app.services.interference import interference_service
from app.services.session_generator import session_generator
from app.config import activity_distribution as activity_distribution_config
from app.repositories.program_repository import ProgramRepository
from app.core.transactions import transactional
from app.core.exceptions import ValidationError, BusinessRuleError


logger = logging.getLogger(__name__)


class ProgramService:
    """
    Generates and manages workout programs.

    A Program spans 8-12 weeks and contains Microcycles (1-2 weeks each).
    Each Microcycle contains Sessions (workout days).

    Goals are distributed across microcycles with weighting to balance
    focus across user's objectives.
    """

    def __init__(self, db: AsyncSession | None = None):
        self._session = db
        self._program_repo = None
        if db:
            self._program_repo = ProgramRepository(db)
    
    @property
    def _program_repo(self) -> ProgramRepository:
        if self.__program_repo is None:
            self.__program_repo = ProgramRepository(self._session)
        return self.__program_repo
    
    @_program_repo.setter
    def _program_repo(self, value):
        self.__program_repo = value
    
    async def create_program_skeleton(
        self,
        user_id: int,
        request: ProgramCreate,
    ) -> Program:
        """
        Create program skeleton with only program entity and disciplines.
        Fast operation that returns immediately.
        
        Microcycles and sessions are generated asynchronously in separate methods.
        
        Args:
            db: Database session
            user_id: User ID
            request: Program creation request
        
        Returns:
            Created Program skeleton (without microcycles/sessions)
        
        Raises:
            ValidationError: If goals invalid, week_count invalid, interference conflict detected
        """
        logger.info("[SKELETON] ProgramService.create_program_skeleton called for user_id=%s", user_id)
        logger.info("[SKELETON] Request data: %s", request.model_dump())
        
        # Validate week count
        if not (8 <= request.duration_weeks <= 12):
            logger.error("[SKELETON] Invalid duration_weeks=%s (must be 8-12)", request.duration_weeks)
            raise ValidationError("duration_weeks", "Program must be 8-12 weeks")
        if request.duration_weeks % 2 != 0:
            logger.error("[SKELETON] Invalid duration_weeks=%s (must be even)", request.duration_weeks)
            raise ValidationError("duration_weeks", "Program must be an even number of weeks")

        # Extract goals from request (1-3 goals allowed)
        goals = request.goals
        logger.info("[SKELETON] Processing %d goals from request", len(goals))
        if not (1 <= len(goals) <= 3):
            logger.error("[SKELETON] Invalid number of goals=%s (must be 1-3)", len(goals))
            raise ValidationError("goals", "1-3 goals required")
        
        # Pad goals list to 3 items if needed (with dummy goal of 0 weight)
        while len(goals) < 3:
            used_goals = {g.goal for g in goals}
            unused_goal = next(g for g in Goal if g not in used_goals)
            goals.append(type(goals[0])(goal=unused_goal, weight=0))
        logger.info("[SKELETON] Goals processed successfully: %s", [(g.goal, g.weight) for g in goals])
        
        # Check for goal interference (only for goals with weight > 0)
        active_goals = [g.goal for g in goals if g.weight > 0]
        if len(active_goals) >= 2:
            logger.info("[SKELETON] Validating %d active goals for interference", len(active_goals))
            validation_goals = active_goals[:]
            while len(validation_goals) < 3:
                validation_goals.append(active_goals[0])
            
            is_valid, warnings = await interference_service.validate_goals(
                self._session, validation_goals[0], validation_goals[1], validation_goals[2]
            )
            if not is_valid:
                logger.error("[SKELETON] Goal validation failed: %s", warnings)
                raise BusinessRuleError("BR_GOAL_INTERFERENCE", f"Goal validation failed: {warnings}")
        
        # Fetch user profile for advanced preferences
        logger.info("[SKELETON] Fetching user profile for user_id=%s", user_id)
        user_profile = await self._session.get(UserProfile, user_id)
        discipline_prefs = user_profile.discipline_preferences if user_profile else None
        scheduling_prefs = dict(user_profile.scheduling_preferences) if user_profile and user_profile.scheduling_preferences else {}
        scheduling_prefs["avoid_cardio_days"] = await self._infer_avoid_cardio_days(self._session, user_id)
        logger.info("[SKELETON] User profile fetched successfully")

        split_template = request.split_template
        if not split_template:
            preference = scheduling_prefs.get("split_template_preference")
            if isinstance(preference, str) and preference.strip() and preference.strip().lower() != "none":
                try:
                    split_template = SplitTemplate[preference.strip().upper()]
                except KeyError:
                    split_template = None
        if not split_template:
            split_template = SplitTemplate.HYBRID
        logger.info("[SKELETON] Using split_template=%s", split_template)

        preferred_cycle_length_days = self._resolve_preferred_microcycle_length_days(scheduling_prefs)
        logger.info("[SKELETON] Preferred microcycle length=%s days", preferred_cycle_length_days)
        
        # Get user for defaults
        user = await self._session.get(User, user_id)
        logger.info("[SKELETON] User fetched for user_id=%s, experience_level=%s", user_id, user.experience_level if user else "unknown")
        
        # Determine progression style if not provided
        progression_style = request.progression_style
        if not progression_style:
            if user and user.experience_level == "beginner":
                progression_style = ProgressionStyle.SINGLE_PROGRESSION
            elif user and user.experience_level in ["advanced", "expert"]:
                progression_style = ProgressionStyle.WAVE_LOADING
            else:
                progression_style = ProgressionStyle.DOUBLE_PROGRESSION
        logger.info("[SKELETON] Using progression_style=%s", progression_style)
        
        # Determine persona settings (from request or user defaults)
        persona_tone = request.persona_tone or (user.persona_tone if user else PersonaTone.SUPPORTIVE)
        persona_aggression = request.persona_aggression or (user.persona_aggression if user else PersonaAggression.BALANCED)
        logger.info("[SKELETON] Persona settings: tone=%s, aggression=%s", persona_tone, persona_aggression)
        
        # Create program
        start_date = request.program_start_date or date.today()
        
        program = Program(
            user_id=user_id,
            name=request.name,
            split_template=split_template,
            days_per_week=request.days_per_week,
            max_session_duration=request.max_session_duration,
            start_date=start_date,
            duration_weeks=request.duration_weeks,
            goal_1=goals[0].goal,
            goal_2=goals[1].goal,
            goal_3=goals[2].goal,
            goal_weight_1=goals[0].weight,
            goal_weight_2=goals[1].weight,
            goal_weight_3=goals[2].weight,
            progression_style=progression_style,
            deload_every_n_microcycles=request.deload_every_n_microcycles or 4,
            persona_tone=persona_tone,
            persona_aggression=persona_aggression,
            is_active=True,
        )
        
        # Deactivate other active programs for this user
        logger.info("[SKELETON] Deactivating other active programs for user_id=%s", user_id)
        await self._program_repo.deactivate_other_programs(user_id, program.id)
        await self._program_repo.create(program)
        logger.info("[SKELETON] Program created with id=%s", program.id)
        
        # Create program disciplines from request or defaults
        logger.info("[SKELETON] Creating program disciplines for program_id=%s", program.id)
        if request.disciplines:
            logger.info("[SKELETON] Using %d disciplines from request", len(request.disciplines))
            for discipline_data in request.disciplines:
                await self._program_repo.add_program_discipline(
                    program.id,
                    discipline_data.discipline,
                    discipline_data.weight
                )
        elif discipline_prefs:
            logger.info("[SKELETON] Using %d discipline preferences", len(discipline_prefs))
            for discipline_type, weight in discipline_prefs.items():
                await self._program_repo.add_program_discipline(program.id, discipline_type, weight)
        else:
            logger.info("[SKELETON] Using fallback disciplines based on experience level=%s", user.experience_level if user else "unknown")
            default_discipline = "bodybuilding"
            default_weight = 10
            if user and user.experience_level == "beginner":
                await self._program_repo.add_program_discipline(program.id, default_discipline, default_weight)
            elif user and user.experience_level == "intermediate":
                await self._program_repo.add_program_discipline(program.id, "bodybuilding", 6)
                await self._program_repo.add_program_discipline(program.id, "powerlifting", 4)
            else:
                await self._program_repo.add_program_discipline(program.id, "bodybuilding", 5)
                await self._program_repo.add_program_discipline(program.id, "powerlifting", 5)
        
        logger.info("[SKELETON] Program skeleton creation completed successfully for program_id=%s", program.id)
        return program
    
    async def create_program(
        self,
        user_id: int,
        request: ProgramCreate,
    ) -> Program:
        """
        DEPRECATED: Use create_program_skeleton + generate_program_structure_async for fast response.
        Kept for backward compatibility.
        """
        return await self.create_program_skeleton(user_id, request)
    
    async def generate_program_structure_async(
        self,
        program_id: int,
    ) -> dict[str, Any]:
        """
        Generate microcycles and session shells asynchronously.
        Runs after program skeleton is created and response returned.
        
        Args:
            program_id: ID of the program to generate structure for
            
        Returns:
            Progress tracking dict
        """
        from app.db.database import async_session_maker
        
        logger.info("[STRUCTURE] Starting program structure generation for program_id=%s", program_id)
        
        async with async_session_maker() as db:
            program = await db.get(Program, program_id)
            if not program:
                logger.error("[STRUCTURE] Program not found: %s", program_id)
                return {"status": "failed", "error": "Program not found"}
            
            user = await db.get(User, program.user_id)
            if not user:
                logger.error("[STRUCTURE] User not found for program_id=%s", program_id)
                return {"status": "failed", "error": "User not found"}
            
            user_profile = await db.get(UserProfile, program.user_id)
            discipline_prefs = user_profile.discipline_preferences if user_profile else None
            scheduling_prefs = dict(user_profile.scheduling_preferences) if user_profile and user_profile.scheduling_preferences else {}
            scheduling_prefs["avoid_cardio_days"] = await self._infer_avoid_cardio_days(db, program.user_id)
            
            total_days = program.duration_weeks * 7
            preferred_cycle_length_days = self._resolve_preferred_microcycle_length_days(scheduling_prefs)
            microcycle_lengths = self._partition_microcycle_lengths(total_days, preferred_cycle_length_days)
            logger.info("[STRUCTURE] Microcycle lengths: %s", microcycle_lengths)
            
            current_date = program.start_date
            deload_frequency = program.deload_every_n_microcycles or 4

            for mc_idx, cycle_length_days in enumerate(microcycle_lengths):
                logger.info("[STRUCTURE] Creating microcycle %d in separate DB session", mc_idx)
                is_deload = ((mc_idx + 1) % deload_frequency == 0)

                split_config = self._build_freeform_split_config(
                    cycle_length_days=cycle_length_days,
                    days_per_week=program.days_per_week,
                )

                split_config = self._apply_goal_based_cycle_distribution(
                    split_config=split_config,
                    goals=[],
                    days_per_week=program.days_per_week,
                    cycle_length_days=cycle_length_days,
                    max_session_duration=program.max_session_duration,
                    user_experience_level=user.experience_level if user else None,
                    scheduling_prefs=scheduling_prefs,
                )

                split_config = self._assign_freeform_day_types_and_focus(
                    split_config=split_config,
                    days_per_week=program.days_per_week,
                )

                try:
                    microcycle = await asyncio.wait_for(
                        self._create_microcycle_in_separate_session(
                            program_id=program.id,
                            user_id=program.user_id,
                            mc_index=mc_idx,
                            start_date=current_date,
                            split_config=split_config,
                            is_deload=is_deload,
                        ),
                        timeout=140,
                    )
                    logger.info("[STRUCTURE] Microcycle %d created with id=%s", mc_idx, microcycle.id)
                    current_date += timedelta(days=cycle_length_days)
                except asyncio.TimeoutError:
                    logger.error("[STRUCTURE] Microcycle %d creation timeout (>140s), skipping", mc_idx)
                    current_date += timedelta(days=cycle_length_days)
                    continue

        logger.info("[STRUCTURE] Program structure generation completed for program_id=%s", program_id)
        return {"status": "completed", "program_id": program_id}

    async def _create_microcycle_in_separate_session(
        self,
        program_id: int,
        user_id: int,
        mc_index: int,
        start_date: date,
        split_config: Dict[str, Any],
        is_deload: bool = False,
    ) -> Microcycle:
        """
        Create a microcycle with sessions in separate DB session.
        Each session created individually to avoid long transactions.

        Args:
            program_id: Parent program ID
            user_id: User ID for session creation
            mc_index: Microcycle index (0-based)
            start_date: Microcycle start date
            split_config: Split template configuration from heuristics
            is_deload: Whether this is a deload microcycle

        Returns:
            Created Microcycle
        """
        from app.db.database import async_session_maker
        from app.repositories.program_repository import ProgramRepository

        async with async_session_maker() as db:
            days_per_cycle = split_config.get("days_per_cycle", 7)
            structure = split_config.get("structure", [])

            status = MicrocycleStatus.ACTIVE if mc_index == 0 else MicrocycleStatus.PLANNED

            microcycle = Microcycle(
                program_id=program_id,
                sequence_number=mc_index + 1,
                start_date=start_date,
                length_days=days_per_cycle,
                status=status,
                is_deload=is_deload,
            )

            repo = ProgramRepository(db)
            await repo.add_microcycle(microcycle)
            await db.commit()
            await db.refresh(microcycle)

            logger.info("[MICROCYCLE] Created microcycle %d with id=%s", mc_index, microcycle.id)

            for day_def in structure:
                session_id = await self._create_session_in_separate_session(
                    microcycle_id=microcycle.id,
                    user_id=user_id,
                    day_num=day_def.get("day", 1),
                    day_type=day_def.get("type", "rest"),
                    focus_patterns=day_def.get("focus", []),
                    start_date=start_date,
                )
                logger.info("[MICROCYCLE] Session created with id=%s for microcycle %d", session_id, microcycle.id)

        return microcycle

    async def _create_session_in_separate_session(
        self,
        microcycle_id: int,
        user_id: int,
        day_num: int,
        day_type: str,
        focus_patterns: list[str],
        start_date: date,
    ) -> Session:
        """
        Create a single session in separate DB session.

        Args:
            microcycle_id: Parent microcycle ID
            user_id: User ID for session creation
            day_num: Day number within microcycle
            day_type: Type of day (rest, upper, lower, etc.)
            focus_patterns: List of focus patterns
            start_date: Microcycle start date

        Returns:
            Created Session
        """
        from app.db.database import async_session_maker
        from app.repositories.program_repository import ProgramRepository

        session_date = start_date + timedelta(days=day_num - 1)
        session_type = self._map_day_type_to_session_type(day_type)

        async with async_session_maker() as db:
            session = Session(
                user_id=user_id,
                microcycle_id=microcycle_id,
                date=session_date,
                day_number=day_num,
                session_type=session_type,
                intent_tags=focus_patterns,
            )

            db.add(session)
            await db.commit()
            await db.refresh(session)

        return session.id

    async def _infer_avoid_cardio_days(self, db: AsyncSession, user_id: int) -> bool:
        try:
            cardio_disciplines = ["cardio", "endurance", "conditioning", "aerobic"]
            cardio_tags = ["cardio", "conditioning", "aerobic"]
            
            result = await db.execute(
                select(UserMovementRule.id)
                .join(MovementDiscipline, MovementDiscipline.movement_id == UserMovementRule.movement_id)
                .join(Movement, Movement.id == MovementDiscipline.movement_id)
                .where(
                    and_(
                        UserMovementRule.user_id == user_id,
                        UserMovementRule.rule_type == MovementRuleType.HARD_NO,
                        or_(
                            MovementDiscipline.discipline.in_([d.value for d in DisciplineType if d.value in cardio_disciplines]),
                        ),
                    )
                )
                .limit(1)
            )
            return result.scalar_one_or_none() is not None
        except Exception:
            try:
                await self._session.rollback()
            except Exception:
                pass
            return False
    
    async def generate_active_microcycle_sessions(
        self,
        program_id: int,
    ) -> dict[str, Any]:
        from app.db.database import async_session_maker

        logger.info(f"[generate_active_microcycle_sessions] START - program_id={program_id}")

        async with async_session_maker() as db:
            program = await db.get(Program, program_id)
            if not program:
                logger.error(f"[generate_active_microcycle_sessions] Program not found: {program_id}")
                return {"status": "failed", "error": "Program not found"}

            result = await db.execute(
                select(Microcycle).where(
                    Microcycle.program_id == program_id,
                    Microcycle.status == MicrocycleStatus.ACTIVE,
                )
            )
            microcycle = result.scalar_one_or_none()
            if not microcycle:
                logger.error(f"[generate_active_microcycle_sessions] Active microcycle not found for program {program_id}")
                return {"status": "failed", "error": "Active microcycle not found"}

            # Set microcycle generation status to IN_PROGRESS
            microcycle.generation_status = GenerationStatus.IN_PROGRESS
            db.add(microcycle)
            await db.commit()
            await db.refresh(microcycle)

        logger.info(f"[generate_active_microcycle_sessions] Found active microcycle {microcycle.id}, starting generation...")

        # Generate sessions sequentially and track progress
        progress = await self._generate_session_content_async(program_id, microcycle.id)

        logger.info(f"[generate_active_microcycle_sessions] COMPLETED for program {program_id}")

        return progress
    
    async def _generate_session_content_async(
        self,
        program_id: int,
        microcycle_id: int,
    ) -> dict[str, Any]:
        """
        Generate exercise content for all non-rest sessions in a microcycle.

        This method creates its own database sessions to avoid holding locks
        during long-running LLM calls.

        Args:
            program_id: ID of the program
            microcycle_id: ID of the microcycle to generate content for

        Returns:
            Progress tracking dict with status and session details
        """
        from app.db.database import async_session_maker

        logger.info(f"[_generate_session_content_async] START - program_id={program_id}, microcycle_id={microcycle_id}")

        # Progress tracking
        progress = {
            "status": "in_progress",
            "program_id": program_id,
            "microcycle_id": microcycle_id,
            "total_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "current_session_id": None,
            "session_progress": [],
        }

        # Create a new DB session for reading program and sessions
        async with async_session_maker() as db:
            # Fetch program and microcycle
            program = await db.get(Program, program_id)
            microcycle = await db.get(Microcycle, microcycle_id)

            if not program or not microcycle:
                logger.error(f"[_generate_session_content_async] FAILED - program={program}, microcycle={microcycle}")
                progress["status"] = "failed"
                progress["error"] = "Program or microcycle not found"
                return progress

            # Get all sessions for this microcycle
            sessions_result = await db.execute(
                select(Session).where(Session.microcycle_id == microcycle.id)
                .order_by(Session.day_number)
            )
            sessions = list(sessions_result.scalars().all())

            logger.info(f"[_generate_session_content_async] Found {len(sessions)} sessions to generate")
            progress["total_sessions"] = len(sessions)

        # Track used movements to ensure variety
        used_movements = set()
        used_movement_groups = {}  # Track usage count by substitution_group
        used_main_patterns = {}    # Track main lift patterns by day
        used_accessory_movements = {}  # Track accessory movements by day

        # Track previous day's muscle volume for interference logic
        previous_day_volume = {}

        # Generate content for each session SEQUENTIALLY
        for session in sessions:
            logger.info(f"[_generate_session_content_async] Processing session {session.id} - type={session.session_type}, day={session.day_number}")
            progress["current_session_id"] = session.id

            # Skip recovery/rest sessions - they get default content
            if session.session_type == SessionType.RECOVERY:
                logger.info(f"[_generate_session_content_async] Skipping RECOVERY session {session.id}")
                # Mark recovery session as completed
                async with async_session_maker() as db:
                    recovery_session = await db.get(Session, session.id)
                    if recovery_session:
                        recovery_session.generation_status = GenerationStatus.COMPLETED
                        db.add(recovery_session)
                        await db.commit()

                previous_day_volume = {}  # Recovery clears fatigue
                progress["completed_sessions"] += 1
                progress["session_progress"].append({
                    "session_id": session.id,
                    "day_number": session.day_number,
                    "session_type": str(session.session_type),
                    "status": "completed",
                    "skipped": True,
                })
                continue

            # Update session generation_status to IN_PROGRESS before generation
            async with async_session_maker() as db:
                session_to_update = await db.get(Session, session.id)
                if session_to_update:
                    session_to_update.generation_status = GenerationStatus.IN_PROGRESS
                    db.add(session_to_update)
                    await db.commit()
                    await db.refresh(session_to_update)

            try:
                # Apply inter-session interference rules for main lift patterns
                async with async_session_maker() as db:
                    session = await self._apply_pattern_interference_rules(
                        db, session, used_main_patterns, microcycle
                    )
            except Exception as e:
                logger.error(
                    f"Failed to apply pattern interference rules for session {session.id}",
                    extra={
                        "event": "pattern_interference_failure",
                        "session_id": session.id,
                        "session_type": str(session.session_type),
                        "day_number": session.day_number,
                        "intent_tags": session.intent_tags,
                        "used_main_patterns": used_main_patterns,
                        "microcycle_id": microcycle.id,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "traceback": traceback.format_exc(),
                    },
                    exc_info=True
                )

            try:
                # Generate and populate session with exercises
                # Each call creates its own DB session
                current_volume = await session_generator.populate_session_by_id(
                    session.id,
                    program_id,
                    microcycle_id,
                    used_movements=list(used_movements),
                    used_movement_groups=dict(used_movement_groups),
                    used_main_patterns=dict(used_main_patterns),
                    used_accessory_movements=dict(used_accessory_movements),
                    previous_day_volume=previous_day_volume,
                )

                # Mark session as COMPLETED after successful generation
                async with async_session_maker() as db:
                    completed_session = await db.get(Session, session.id)
                    if completed_session:
                        completed_session.generation_status = GenerationStatus.COMPLETED
                        db.add(completed_session)
                        await db.commit()

                progress["completed_sessions"] += 1
                progress["session_progress"].append({
                    "session_id": session.id,
                    "day_number": session.day_number,
                    "session_type": str(session.session_type),
                    "status": "completed",
                })

            except Exception as e:
                logger.error(
                    f"Failed to generate content for session {session.id}",
                    extra={
                        "event": "session_generation_failed",
                        "session_id": session.id,
                        "session_type": str(session.session_type),
                        "day_number": session.day_number,
                        "intent_tags": session.intent_tags,
                        "program_id": program_id,
                        "microcycle_id": microcycle_id,
                        "used_movements_count": len(used_movements),
                        "previous_day_volume": previous_day_volume,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "traceback": traceback.format_exc(),
                    },
                    exc_info=True
                )

                # Robust Fallback: Mark session as failed but "content present" so spinner stops
                try:
                    async with async_session_maker() as db:
                        failed_session = await db.get(Session, session.id)
                        if failed_session:
                            failed_session.coach_notes = f"Generation failed: {str(e)}. Please regenerate."
                            # Mark as FAILED
                            failed_session.generation_status = GenerationStatus.FAILED
                            db.add(failed_session)
                            await db.commit()
                except Exception as fallback_error:
                    logger.error(
                        f"Failed to apply fallback for session {session.id}",
                        extra={
                            "event": "session_generation_fallback_failed",
                            "session_id": session.id,
                            "original_exception": str(e),
                            "fallback_exception_type": type(fallback_error).__name__,
                            "fallback_exception_message": str(fallback_error),
                            "traceback": traceback.format_exc(),
                        },
                        exc_info=True
                    )

                progress["failed_sessions"] += 1
                progress["session_progress"].append({
                    "session_id": session.id,
                    "day_number": session.day_number,
                    "session_type": str(session.session_type),
                    "status": "failed",
                    "error": str(e),
                })

                # Skip tracking for this session so others can still be generated
                previous_day_volume = {}
                continue

            # Update previous volume for next iteration
            previous_day_volume = current_volume

            # Track used movements and movement groups
            if current_volume:
                # Re-fetch session to get updated content
                async with async_session_maker() as db:
                    stmt = select(Session).options(
                        selectinload(Session.exercises).selectinload(SessionExercise.movement)
                    ).where(Session.id == session.id)
                    result = await db.execute(stmt)
                    updated_session = result.scalar_one_or_none()

                    if updated_session:
                        # Track individual movements
                        session_movements = []
                        main_patterns_used = []
                        accessory_movements_used = []

                        if updated_session.exercises:
                            for ex in updated_session.exercises:
                                if ex.movement:
                                    name = ex.movement.name
                                    session_movements.append(name)

                                    # Treat finisher as accessory for interference
                                    if ex.exercise_role in [ExerciseRole.ACCESSORY, ExerciseRole.FINISHER]:
                                        accessory_movements_used.append(name)

                        # Update tracking sets
                        for movement_name in session_movements:
                            used_movements.add(movement_name)

                        # Track main lift patterns for this session
                        if updated_session.intent_tags:
                            main_patterns_used = updated_session.intent_tags[:2]
                            used_main_patterns[session.day_number] = main_patterns_used

                        # Track accessory movements for this session
                        used_accessory_movements[session.day_number] = accessory_movements_used

                        # Update movement group usage counts
                        await self._update_movement_group_usage(
                            db, session_movements, used_movement_groups
                        )

        # Set microcycle generation_status after all sessions complete
        async with async_session_maker() as db:
            final_microcycle = await db.get(Microcycle, microcycle_id)
            if final_microcycle:
                if progress["failed_sessions"] > 0:
                    final_microcycle.generation_status = GenerationStatus.FAILED
                else:
                    final_microcycle.generation_status = GenerationStatus.COMPLETED
                db.add(final_microcycle)
                await db.commit()

        progress["status"] = "completed"
        progress["current_session_id"] = None
        logger.info(f"[_generate_session_content_async] COMPLETED - {progress['completed_sessions']} sessions completed, {progress['failed_sessions']} failed")

        return progress
    
    async def _apply_pattern_interference_rules(
        self,
        db: AsyncSession,
        session: Session,
        used_main_patterns: dict[int, list[str]],
        microcycle: Microcycle,
    ) -> Session:
        """
        Apply inter-session interference rules for main lift patterns.
        
        Rules:
        1. No same main pattern on consecutive days (even with rest day between)
        2. No same main pattern on back-to-back training days
        3. Prioritize pattern diversity: squat -> hinge -> lunge rotation for lower body
        4. Enforce minimum 2-day gap for same main pattern
        
        Args:
            db: Database session
            session: Session to apply rules to
            used_main_patterns: Dict mapping day_number to list of main patterns used
            microcycle: Parent microcycle
            
        Returns:
            Session with updated intent_tags based on interference rules
        """
        if session.session_type == SessionType.RECOVERY:
            return session
        if session.session_type in {SessionType.CARDIO, SessionType.MOBILITY}:
            return session
        if session.session_type == SessionType.CUSTOM and "conditioning" in (session.intent_tags or []):
            return session
        
        current_day = session.day_number
        current_patterns = session.intent_tags or []
        
        # Get all training days in this microcycle for context
        training_days = sorted([day for day, patterns in used_main_patterns.items() if patterns])
        
        # Define pattern alternatives for intelligent substitution
        pattern_alternatives = {
            # Lower body pattern rotation
            "squat": ["hinge", "lunge"],
            "hinge": ["squat", "lunge"], 
            "lunge": ["squat", "hinge"],
            
            # Upper body pattern rotation
            "horizontal_push": ["vertical_push"],
            "vertical_push": ["horizontal_push"],
            "horizontal_pull": ["vertical_pull"],
            "vertical_pull": ["horizontal_pull"],
        }
        
        # Check for pattern conflicts and resolve them
        conflicting_patterns = []
        for pattern in current_patterns[:2]:  # Only check main patterns (first 2)
            if self._has_pattern_conflict(pattern, current_day, used_main_patterns):
                conflicting_patterns.append(pattern)
        
        # Replace conflicting patterns with alternatives
        if conflicting_patterns:
            new_patterns = current_patterns.copy()
            
            for i, pattern in enumerate(current_patterns[:2]):
                if pattern in conflicting_patterns:
                    # Find alternative pattern
                    alternative = self._find_alternative_pattern(
                        pattern, current_day, used_main_patterns, pattern_alternatives
                    )
                    if alternative:
                        new_patterns[i] = alternative
                        logger.info(
                            f"Day {current_day}: Replaced conflicting pattern '{pattern}' "
                            f"with '{alternative}' due to interference rules"
                        )
            
            # Update session intent_tags
            session.intent_tags = new_patterns
            db.add(session)
            await db.flush()
        
        return session
    
    def _has_pattern_conflict(
        self,
        pattern: str,
        current_day: int,
        used_main_patterns: dict[int, list[str]],
    ) -> bool:
        """
        Check if a pattern conflicts with interference rules.
        
        Args:
            pattern: Pattern to check (e.g., "squat")
            current_day: Current day number
            used_main_patterns: Dict of day -> patterns used
            
        Returns:
            True if pattern conflicts with interference rules
        """
        # Rule 1: No same pattern on consecutive training days
        prev_day = current_day - 1
        if prev_day in used_main_patterns:
            prev_patterns = used_main_patterns[prev_day][:2]  # Main patterns only
            if pattern in prev_patterns:
                return True
        
        # Rule 2: No same pattern within 2 days (even with rest day between)
        for check_day in range(max(1, current_day - 2), current_day):
            if check_day in used_main_patterns:
                check_patterns = used_main_patterns[check_day][:2]
                if pattern in check_patterns:
                    return True
        
        # Rule 3: Limit pattern usage to max 2 times per week (7 days)
        pattern_count = 0
        week_start = max(1, current_day - 6)
        for check_day in range(week_start, current_day + 1):
            if check_day in used_main_patterns:
                check_patterns = used_main_patterns[check_day][:2]
                if pattern in check_patterns:
                    pattern_count += 1
        
        if pattern_count >= 2:  # Already used twice this week
            return True
        
        return False
    
    def _find_alternative_pattern(
        self,
        original_pattern: str,
        current_day: int,
        used_main_patterns: dict[int, list[str]],
        pattern_alternatives: dict[str, list[str]],
    ) -> str | None:
        """
        Find an alternative pattern that doesn't conflict with interference rules.
        
        Args:
            original_pattern: Pattern that conflicts
            current_day: Current day number
            used_main_patterns: Dict of day -> patterns used
            pattern_alternatives: Dict of pattern -> list of alternatives
            
        Returns:
            Alternative pattern or None if no suitable alternative found
        """
        alternatives = pattern_alternatives.get(original_pattern, [])
        
        for alternative in alternatives:
            if not self._has_pattern_conflict(alternative, current_day, used_main_patterns):
                return alternative
        
        # Fallback: try all lower body patterns if original was lower body
        lower_body_patterns = ["squat", "hinge", "lunge"]
        upper_body_patterns = ["horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull"]
        
        if original_pattern in lower_body_patterns:
            for pattern in lower_body_patterns:
                if pattern != original_pattern and not self._has_pattern_conflict(
                    pattern, current_day, used_main_patterns
                ):
                    return pattern
        elif original_pattern in upper_body_patterns:
            for pattern in upper_body_patterns:
                if pattern != original_pattern and not self._has_pattern_conflict(
                    pattern, current_day, used_main_patterns
                ):
                    return pattern
        
        return None
    
    async def _update_movement_group_usage(
        self,
        db: AsyncSession,
        session_movements: list[str],
        used_movement_groups: dict[str, int],
    ) -> None:
        """
        Update movement group usage counts for variety tracking.
        
        Args:
            db: Database session
            session_movements: List of movement names used in this session
            used_movement_groups: Dict tracking usage count by substitution_group
        """
        if not session_movements:
            return
        
        # Get movement objects to access substitution_group
        movements_result = await db.execute(
            select(Movement).where(Movement.name.in_(session_movements))
        )
        movements = {m.name: m for m in movements_result.scalars().all()}
        
        # Update group usage counts
        for movement_name in session_movements:
            movement = movements.get(movement_name)
            if movement and movement.substitution_group:
                group = movement.substitution_group
                used_movement_groups[group] = used_movement_groups.get(group, 0) + 1
    
    async def _create_microcycle(
        self,
        program_id: int,
        user_id: int,
        mc_index: int,
        start_date: date,
        split_config: Dict[str, Any],
        is_deload: bool = False,
    ) -> Microcycle:
        """
        Create a microcycle with sessions based on split template.

        Args:
            program_id: Parent program ID
            user_id: User ID for session creation
            mc_index: Microcycle index (0-based)
            start_date: Microcycle start date
            split_config: Split template configuration from heuristics
            is_deload: Whether this is a deload microcycle

        Returns:
            Created Microcycle
        """
        days_per_cycle = split_config.get("days_per_cycle", 7)
        structure = split_config.get("structure", [])

        # First microcycle is active, others are planned
        status = MicrocycleStatus.ACTIVE if mc_index == 0 else MicrocycleStatus.PLANNED

        microcycle = Microcycle(
            program_id=program_id,
            sequence_number=mc_index + 1,  # 1-indexed
            start_date=start_date,
            length_days=days_per_cycle,
            status=status,
            is_deload=is_deload,
        )
        await self._program_repo.add_microcycle(microcycle)

        # Create sessions from split template structure
        for day_def in structure:
            day_num = day_def.get("day", 1)
            day_type = day_def.get("type", "rest")
            focus_patterns = day_def.get("focus", [])

            # Calculate session date
            session_date = start_date + timedelta(days=day_num - 1)

            # Map day type to SessionType enum
            session_type = self._map_day_type_to_session_type(day_type)

            # Create session (even for rest days - they can have recovery activities)
            session = Session(
                user_id=user_id,
                microcycle_id=microcycle.id,
                date=session_date,
                day_number=day_num,
                session_type=session_type,
                intent_tags=focus_patterns,
            )
            self._program_repo.add_session(session)

        return microcycle

    def _resolve_preferred_microcycle_length_days(self, scheduling_prefs: dict[str, Any]) -> int:
        preferred = scheduling_prefs.get("microcycle_length_days")
        if isinstance(preferred, int) and 7 <= preferred <= 14:
            return preferred
        return activity_distribution_config.default_microcycle_length_days

    def _partition_microcycle_lengths(self, total_days: int, preferred_length_days: int) -> list[int]:
        if total_days <= 0:
            return []

        preferred_length_days = min(14, max(7, int(preferred_length_days)))
        count = max(1, int(round(total_days / preferred_length_days)))

        for _ in range(50):
            base = total_days // count
            remainder = total_days % count
            if base < 7:
                count = max(1, count - 1)
                continue
            if base > 14 or (base == 14 and remainder > 0):
                count += 1
                continue
            break

        base = total_days // count
        remainder = total_days % count
        lengths = [base + 1] * remainder + [base] * (count - remainder)
        return lengths

    def _pick_evenly_spaced_days(self, cycle_length_days: int, session_count: int) -> list[int]:
        cycle_length_days = max(1, int(cycle_length_days))
        session_count = max(0, min(int(session_count), cycle_length_days))
        if session_count == 0:
            return []
        if session_count == cycle_length_days:
            return list(range(1, cycle_length_days + 1))

        step = cycle_length_days / session_count
        taken: set[int] = set()
        chosen: list[int] = []
        for k in range(session_count):
            ideal = int(round((k + 0.5) * step))
            day = min(cycle_length_days, max(1, ideal))
            while day in taken and day < cycle_length_days:
                day += 1
            while day in taken and day > 1:
                day -= 1
            taken.add(day)
            chosen.append(day)
        return sorted(chosen)

    def _build_freeform_split_config(self, cycle_length_days: int, days_per_week: int) -> dict[str, Any]:
        cycle_length_days = min(14, max(7, int(cycle_length_days)))
        target_sessions = int(round(days_per_week * (cycle_length_days / 7.0)))
        target_sessions = max(2, min(target_sessions, cycle_length_days))
        training_days = set(self._pick_evenly_spaced_days(cycle_length_days, target_sessions))
        structure: list[dict[str, Any]] = []
        for day in range(1, cycle_length_days + 1):
            if day in training_days:
                structure.append({"day": day, "type": "full_body", "focus": []})
            else:
                structure.append({"day": day, "type": "rest"})
        return {
            "days_per_cycle": cycle_length_days,
            "structure": structure,
            "training_days": len(training_days),
            "rest_days": cycle_length_days - len(training_days),
        }

    def _assign_freeform_day_types_and_focus(self, split_config: dict[str, Any], days_per_week: int) -> dict[str, Any]:
        structure = [dict(d) for d in (split_config.get("structure") or [])]
        lifting_indexes = [
            i
            for i, d in enumerate(structure)
            if (d.get("type") or "rest") not in {"rest", "recovery", "cardio", "mobility", "conditioning"}
        ]

        if days_per_week <= 3:
            type_cycle = ["full_body"]
        elif days_per_week == 4:
            type_cycle = ["upper", "lower", "upper", "lower", "full_body"]
        elif days_per_week == 5:
            type_cycle = ["upper", "lower", "full_body", "upper", "lower"]
        else:
            type_cycle = ["push", "pull", "legs", "upper", "lower", "full_body"]

        lower_cycle = ["squat", "hinge", "lunge"]
        push_cycle = ["horizontal_push", "vertical_push"]
        pull_cycle = ["horizontal_pull", "vertical_pull"]
        lower_idx = 0
        push_idx = 0
        pull_idx = 0

        for seq, i in enumerate(lifting_indexes):
            day_type = type_cycle[seq % len(type_cycle)]
            existing_focus = structure[i].get("focus") or []
            if not isinstance(existing_focus, list):
                existing_focus = []
            tags = [t for t in existing_focus if t.startswith("prefer_")]

            if day_type == "upper":
                patterns = [push_cycle[push_idx % len(push_cycle)], pull_cycle[pull_idx % len(pull_cycle)]]
                push_idx += 1
                pull_idx += 1
            elif day_type in {"lower", "legs"}:
                patterns = [lower_cycle[lower_idx % len(lower_cycle)], lower_cycle[(lower_idx + 1) % len(lower_cycle)]]
                lower_idx += 1
            elif day_type == "push":
                patterns = [push_cycle[push_idx % len(push_cycle)], push_cycle[(push_idx + 1) % len(push_cycle)]]
                push_idx += 1
            elif day_type == "pull":
                patterns = [pull_cycle[pull_idx % len(pull_cycle)], pull_cycle[(pull_idx + 1) % len(pull_cycle)]]
                pull_idx += 1
            else:
                patterns = [
                    lower_cycle[lower_idx % len(lower_cycle)],
                    push_cycle[push_idx % len(push_cycle)],
                    pull_cycle[pull_idx % len(pull_cycle)],
                ]
                lower_idx += 1
                push_idx += 1
                pull_idx += 1

            structure[i]["type"] = day_type
            structure[i]["focus"] = patterns + tags

        split_config["structure"] = structure
        return split_config

    def _apply_goal_based_cycle_distribution(
        self,
        split_config: dict[str, Any],
        goals: list[Any],
        days_per_week: int,
        cycle_length_days: int,
        max_session_duration: int,
        user_experience_level: str | None,
        scheduling_prefs: dict,
    ) -> dict[str, Any]:
        if not split_config or not split_config.get("structure"):
            return split_config

        goal_weights: dict[str, int] = {"strength": 0, "hypertrophy": 0, "endurance": 0, "fat_loss": 0, "mobility": 0}
        for g in goals or []:
            goal_value = getattr(getattr(g, "goal", None), "value", None)
            weight_value = getattr(g, "weight", None)
            if goal_value in goal_weights and isinstance(weight_value, int):
                goal_weights[goal_value] = weight_value

        bucket_scores: dict[str, float] = {"cardio": 0.0, "finisher": 0.0, "mobility": 0.0, "lifting": 0.0}
        for goal, weight in goal_weights.items():
            weights_map = activity_distribution_config.goal_bucket_weights.get(goal, {}) or {}
            for bucket, share in weights_map.items():
                bucket_scores[bucket] = bucket_scores.get(bucket, 0.0) + (float(weight) * float(share))

        structure = [dict(d) for d in split_config["structure"]]

        def is_rest_day(d: dict[str, Any]) -> bool:
            return (d.get("type") or "rest") == "rest"

        training_days_in_cycle = sum(1 for d in structure if not is_rest_day(d))
        total_cycle_minutes = max(0, int(training_days_in_cycle * max_session_duration))
        cardio_minutes = int(total_cycle_minutes * (bucket_scores.get("cardio", 0.0) / 10.0))
        mobility_minutes = int(total_cycle_minutes * (bucket_scores.get("mobility", 0.0) / 10.0))
        finisher_minutes = int(total_cycle_minutes * (bucket_scores.get("finisher", 0.0) / 10.0))
        cardio_minutes = min(cardio_minutes, int(total_cycle_minutes * activity_distribution_config.cardio_max_pct))
        mobility_minutes = min(mobility_minutes, int(total_cycle_minutes * activity_distribution_config.mobility_max_pct))

        cardio_signal = goal_weights["endurance"] + goal_weights["fat_loss"]
        strength_signal = goal_weights["strength"] + goal_weights["hypertrophy"]

        experience = (user_experience_level or "").lower()
        beginner = experience == "beginner"
        overtraining_risk = days_per_week >= 6

        cardio_preference = scheduling_prefs.get("cardio_preference") or "finisher"
        avoid_cardio_days = bool(scheduling_prefs.get("avoid_cardio_days"))
        dedicated_day_mode = cardio_preference == "dedicated_day"

        preferred_dedicated_type = "cardio"
        if dedicated_day_mode:
            if avoid_cardio_days:
                preferred_dedicated_type = "conditioning"
            else:
                preferred_dedicated_type = "cardio" if goal_weights["endurance"] >= goal_weights["fat_loss"] else "conditioning"

        endurance_cardio_policy = scheduling_prefs.get("endurance_dedicated_cardio_day_policy") or "default"
        if endurance_cardio_policy not in {"default", "always", "never"}:
            endurance_cardio_policy = "default"
        endurance_heavy = goal_weights["endurance"] >= int(activity_distribution_config.endurance_heavy_dedicated_cardio_day_min_weight)
        force_endurance_cardio_day = (
            endurance_heavy
            and cycle_length_days >= int(activity_distribution_config.endurance_heavy_dedicated_cardio_day_min_cycle_length_days)
            and endurance_cardio_policy != "never"
            and (
                endurance_cardio_policy == "always"
                or bool(activity_distribution_config.endurance_heavy_dedicated_cardio_day_default)
            )
        )
        force_endurance_dedicated_type = "conditioning" if avoid_cardio_days else "cardio"

        allow_cardio_only = (
            cardio_preference in {"mixed"}
            or bool(scheduling_prefs.get("allow_cardio_only_days"))
            or overtraining_risk
            or beginner
            or (cardio_preference == "finisher" and cardio_signal >= 8)
            or (force_endurance_cardio_day and force_endurance_dedicated_type == "cardio")
        )
        allow_conditioning_only = (
            cardio_preference in {"mixed"}
            or bool(scheduling_prefs.get("allow_conditioning_only_days"))
            or (force_endurance_cardio_day and force_endurance_dedicated_type == "conditioning")
        ) and (not overtraining_risk)

        if dedicated_day_mode:
            allow_cardio_only = preferred_dedicated_type == "cardio" or (force_endurance_cardio_day and force_endurance_dedicated_type == "cardio")
            allow_conditioning_only = preferred_dedicated_type == "conditioning"

        if avoid_cardio_days:
            allow_cardio_only = False

        training_indexes = [i for i, d in enumerate(structure) if not is_rest_day(d)]
        lifting_indexes = [i for i in training_indexes if (structure[i].get("type") or "") not in {"cardio", "mobility"}]

        min_lifting_days = 2 if len(lifting_indexes) >= 2 else len(lifting_indexes)
        max_convertible = max(0, len(lifting_indexes) - min_lifting_days)

        def can_convert_lifting_day(idx: int) -> bool:
            day_type = structure[idx].get("type")
            if day_type == "upper":
                return sum(1 for i in lifting_indexes if structure[i].get("type") == "upper") > 1
            if day_type == "lower":
                return sum(1 for i in lifting_indexes if structure[i].get("type") == "lower") > 1
            return True

        convert_candidates = [i for i in reversed(lifting_indexes) if can_convert_lifting_day(i)]

        cycle_blocks = max(1, int(round(max(7, int(cycle_length_days)) / 7)))

        conditioning_days = 0
        available_conditioning_days = int(finisher_minutes // max(1, activity_distribution_config.min_conditioning_minutes))
        desired_conditioning_days = min(cycle_blocks, available_conditioning_days, max_convertible, len(convert_candidates))
        if force_endurance_cardio_day and force_endurance_dedicated_type == "conditioning" and desired_conditioning_days == 0 and max_convertible > 0 and len(convert_candidates) > 0:
            desired_conditioning_days = 1
        if dedicated_day_mode and preferred_dedicated_type == "conditioning" and desired_conditioning_days == 0 and max_convertible > 0 and len(convert_candidates) > 0:
            desired_conditioning_days = 1
        if allow_conditioning_only and desired_conditioning_days > 0:
            for _ in range(desired_conditioning_days):
                idx = convert_candidates.pop(0)
                structure[idx]["type"] = "conditioning"
                structure[idx]["focus"] = ["conditioning"]
                conditioning_days += 1
                max_convertible -= 1

        cardio_days = 0
        available_cardio_days = int(cardio_minutes // max(1, max_session_duration))
        desired_cardio_days = min(cycle_blocks, available_cardio_days, max_convertible, len(convert_candidates))
        if force_endurance_cardio_day and desired_cardio_days == 0 and max_convertible > 0 and len(convert_candidates) > 0:
            desired_cardio_days = 1
        if dedicated_day_mode and preferred_dedicated_type == "cardio" and desired_cardio_days == 0 and max_convertible > 0 and len(convert_candidates) > 0:
            desired_cardio_days = 1
        if allow_cardio_only and desired_cardio_days > 0:
            for _ in range(desired_cardio_days):
                idx = convert_candidates.pop(0)
                structure[idx]["type"] = "cardio"
                cardio_focus = ["cardio"]
                cardio_focus.append("endurance" if goal_weights["endurance"] >= goal_weights["fat_loss"] else "fat_loss")
                structure[idx]["focus"] = cardio_focus
                cardio_days += 1
                max_convertible -= 1

        lifting_after = [i for i, d in enumerate(structure) if not is_rest_day(d) and (d.get("type") or "") not in {"cardio", "mobility", "conditioning"}]
        if lifting_after:
            desired_accessory_days = 1 if strength_signal > 0 else 0
            remaining_cardio_minutes = max(0, cardio_minutes - (cardio_days * max_session_duration))
            remaining_finisher_minutes = max(0, finisher_minutes + remaining_cardio_minutes)

            desired_finisher_days = 0
            if cardio_signal >= 4 and remaining_finisher_minutes > 0:
                desired_finisher_days = max(
                    1,
                    round(remaining_finisher_minutes / max(1, activity_distribution_config.default_finisher_minutes)),
                )
            desired_finisher_days = min(desired_finisher_days, max(0, len(lifting_after) - desired_accessory_days))

            finisher_targets = set(lifting_after[:desired_finisher_days])
            accessory_targets = set(lifting_after[desired_finisher_days:desired_finisher_days + desired_accessory_days])

            for i in lifting_after:
                focus = structure[i].get("focus") or []
                if not isinstance(focus, list):
                    focus = []
                if i in finisher_targets and "prefer_finisher" not in focus:
                    focus.append("prefer_finisher")
                if i in accessory_targets and "prefer_accessory" not in focus:
                    focus.append("prefer_accessory")
                structure[i]["focus"] = focus

        split_config["structure"] = structure
        split_config["training_days"] = sum(1 for d in structure if not is_rest_day(d))
        split_config["rest_days"] = sum(1 for d in structure if is_rest_day(d))
        split_config["goal_weights"] = goal_weights
        split_config["goal_bias_rationale"] = activity_distribution_config.BIAS_RATIONALE
        return split_config
    

    def _map_day_type_to_session_type(self, day_type: str) -> SessionType:
        """
        Map split template day type to SessionType enum.
        """
        mapping = {
            "upper": SessionType.UPPER,
            "lower": SessionType.LOWER,
            "push": SessionType.PUSH,
            "pull": SessionType.PULL,
            "legs": SessionType.LEGS,
            "full_body": SessionType.FULL_BODY,
            "cardio": SessionType.CARDIO,
            "mobility": SessionType.MOBILITY,
            "conditioning": SessionType.CUSTOM,
            "rest": SessionType.RECOVERY,
            "recovery": SessionType.RECOVERY,
        }
        return mapping.get(day_type.lower(), SessionType.CUSTOM)
    
    async def get_program(
        self,
        db: AsyncSession,
        program_id: int,
        user_id: int,
    ) -> Optional[Program]:
        """
        Retrieve a program with all microcycles and sessions.
        
        Args:
            db: Database session
            program_id: Program ID
            user_id: User ID
        
        Returns:
            Program object or None if not found
        """
        result = await db.execute(
            select(Program).where(
                and_(
                    Program.id == program_id,
                    Program.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def list_programs(
        self,
        user_id: int,
        status: Optional[str] = None,
    ) -> list:
        """
        List all programs for user, optionally filtered by status.

        Args:
            user_id: User ID
            status: Optional ProgramStatus filter

        Returns:
            List of Program objects
        """
        filter_dict = {"user_id": user_id}
        if status:
            filter_dict["status"] = status
        
        pagination_params = PaginationParams(
            limit=1000,
            cursor=None,
            direction="next"
        )
        
        result = await self._program_repo.list(filter_dict, pagination_params)
        return result.items


# Singleton instance
program_service = ProgramService()
