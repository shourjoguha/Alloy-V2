"""
Admin API routes for system management and maintenance tasks.
"""
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy import select, and_, func, text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import Program, Session, Microcycle, SessionExercise, MicrocycleStatus, GenerationStatus
from app.services.session_generator import SessionGeneratorService
from app.services.program import program_service
from app.api.routes.dependencies import get_current_user_id
from app.core.exceptions import NotFoundError, AuthorizationError
from fastapi import HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


# Generation status values as strings (matching database enum)
GENERATION_STATUS_PENDING = "pending"
GENERATION_STATUS_GENERATING = "generating"
GENERATION_STATUS_COMPLETED = "completed"
GENERATION_STATUS_FAILED = "failed"


async def count_session_exercises(session_id: int, db: AsyncSession) -> int:
    """Count number of exercises for a given session."""
    result = await db.execute(
        select(func.count(SessionExercise.id)).where(SessionExercise.session_id == session_id)
    )
    return result.scalar() or 0


@router.get("/programs/{program_id}/sessions/summary")
async def get_program_sessions_summary(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get a summary of sessions for a program, including counts by generation status.

    This is a diagnostic endpoint to identify sessions with missing exercises.
    """
    # Verify user has access to this program
    program = await db.get(Program, program_id)
    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})

    if program.user_id != user_id:
        raise AuthorizationError("Access denied to this program", details={"program_id": program_id, "user_id": user_id})

    # Get microcycles for this program
    microcycles_stmt = select(Microcycle.id).where(Microcycle.program_id == program_id)
    microcycle_result = await db.execute(microcycles_stmt)
    microcycle_ids = [row[0] for row in microcycle_result.fetchall()]

    if not microcycle_ids:
        return {
            "program_id": program_id,
            "program_name": program.name,
            "total_sessions": 0,
            "sessions_by_status": {},
            "sessions_with_zero_exercises_by_status": {},
        }

    # Count total sessions
    total_stmt = select(func.count(Session.id)).where(Session.microcycle_id.in_(microcycle_ids))
    total_result = await db.execute(total_stmt)
    total_sessions = total_result.scalar() or 0

    # Count sessions by generation_status using raw SQL
    sessions_by_status = {}
    for status_name, status_value in [
        ("PENDING", GENERATION_STATUS_PENDING),
        ("GENERATING", GENERATION_STATUS_GENERATING),
        ("COMPLETED", GENERATION_STATUS_COMPLETED),
        ("FAILED", GENERATION_STATUS_FAILED),
    ]:
        count_stmt = text("""
            SELECT COUNT(*) FROM sessions
            WHERE microcycle_id = ANY(:microcycle_ids)
            AND generation_status = CAST(:status AS generation_status)
        """).bindparams(bindparam("microcycle_ids"), bindparam("status"))
        result = await db.execute(
            count_stmt,
            {"microcycle_ids": microcycle_ids, "status": status_value}
        )
        count = result.scalar() or 0
        sessions_by_status[status_name] = count

    # Count sessions with 0 exercises by status
    sessions_with_zero_exercises_by_status = {}
    for status_name, status_value in [
        ("PENDING", GENERATION_STATUS_PENDING),
        ("GENERATING", GENERATION_STATUS_GENERATING),
        ("COMPLETED", GENERATION_STATUS_COMPLETED),
        ("FAILED", GENERATION_STATUS_FAILED),
    ]:
        # Get session IDs for this status
        sessions_stmt = text("""
            SELECT id FROM sessions
            WHERE microcycle_id = ANY(:microcycle_ids)
            AND generation_status = CAST(:status AS generation_status)
        """).bindparams(bindparam("microcycle_ids"), bindparam("status"))
        result = await db.execute(
            sessions_stmt,
            {"microcycle_ids": microcycle_ids, "status": status_value}
        )
        session_ids = [row[0] for row in result.fetchall()]

        if not session_ids:
            sessions_with_zero_exercises_by_status[status_name] = 0
            continue

        # Count sessions with 0 exercises
        zero_exercise_count = 0
        for session_id in session_ids:
            exercise_count = await count_session_exercises(session_id, db)
            if exercise_count == 0:
                zero_exercise_count += 1

        sessions_with_zero_exercises_by_status[status_name] = zero_exercise_count

    return {
        "program_id": program_id,
        "program_name": program.name,
        "user_id": program.user_id,
        "total_sessions": total_sessions,
        "sessions_by_status": sessions_by_status,
        "sessions_with_zero_exercises_by_status": sessions_with_zero_exercises_by_status,
    }


@router.post("/programs/{program_id}/sessions/fix-pending-zero-exercises")
async def fix_pending_sessions_with_zero_exercises(
    program_id: int,
    background_tasks: BackgroundTasks,
    regenerate: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Fix sessions with 0 exercises and PENDING status by setting them to FAILED.

    Optionally regenerate sessions after marking them as FAILED.

    Args:
        program_id: The ID of the program to fix
        regenerate: If True, regenerate the sessions after marking as FAILED

    Returns:
        Summary of changes made
    """
    # Verify user has access to this program
    program = await db.get(Program, program_id)
    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})

    if program.user_id != user_id:
        raise AuthorizationError("Access denied to this program", details={"program_id": program_id, "user_id": user_id})

    # Get microcycles for this program
    microcycles_stmt = select(Microcycle.id).where(Microcycle.program_id == program_id)
    microcycle_result = await db.execute(microcycles_stmt)
    microcycle_ids = [row[0] for row in microcycle_result.fetchall()]

    if not microcycle_ids:
        return {
            "program_id": program_id,
            "message": "No microcycles found for this program",
            "sessions_updated": 0,
        }

    # Find all sessions with PENDING status using raw SQL
    pending_sessions_stmt = text("""
        SELECT id FROM sessions
        WHERE microcycle_id = ANY(:microcycle_ids)
        AND generation_status = CAST(:status AS generation_status)
    """).bindparams(bindparam("microcycle_ids"), bindparam("status"))
    result = await db.execute(
        pending_sessions_stmt,
        {"microcycle_ids": microcycle_ids, "status": GENERATION_STATUS_PENDING}
    )
    pending_session_ids = [row[0] for row in result.fetchall()]

    # Filter sessions with 0 exercises
    sessions_to_fix = []
    for session_id in pending_session_ids:
        exercise_count = await count_session_exercises(session_id, db)
        if exercise_count == 0:
            session = await db.get(Session, session_id)
            if session:
                sessions_to_fix.append(session)

    if not sessions_to_fix:
        return {
            "program_id": program_id,
            "message": "No sessions with 0 exercises and PENDING status found",
            "sessions_updated": 0,
            "regenerate_queued": False,
        }

    # Set generation_status to FAILED
    updated_count = 0
    for session in sessions_to_fix:
        session.generation_status = GENERATION_STATUS_FAILED
        db.add(session)
        updated_count += 1

    await db.commit()

    logger.info(
        f"Marked {updated_count} sessions as FAILED for program {program_id} "
        f"(user {user_id})"
    )

    # Queue regeneration if requested
    regenerate_queued = False
    if regenerate:
        background_tasks.add_task(
            regenerate_sessions_for_program,
            program_id=program_id,
            session_ids=[s.id for s in sessions_to_fix]
        )
        regenerate_queued = True
        logger.info(
            f"Queued regeneration of {len(sessions_to_fix)} sessions for program {program_id}"
        )

    return {
        "program_id": program_id,
        "message": f"Successfully marked {updated_count} sessions as FAILED",
        "sessions_updated": updated_count,
        "session_ids": [s.id for s in sessions_to_fix],
        "regenerate_queued": regenerate_queued,
    }


@router.post("/programs/{program_id}/sessions/regenerate-failed")
async def regenerate_failed_sessions(
    program_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Regenerate all sessions with FAILED status for a program.

    This queues a background task to regenerate sessions.
    """
    # Verify user has access to this program
    program = await db.get(Program, program_id)
    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})

    if program.user_id != user_id:
        raise AuthorizationError("Access denied to this program", details={"program_id": program_id, "user_id": user_id})

    # Get microcycles for this program
    microcycles_stmt = select(Microcycle.id).where(Microcycle.program_id == program_id)
    microcycle_result = await db.execute(microcycles_stmt)
    microcycle_ids = [row[0] for row in microcycle_result.fetchall()]

    if not microcycle_ids:
        return {
            "program_id": program_id,
            "message": "No microcycles found for this program",
            "sessions_queued": 0,
        }

    # Find all sessions with FAILED status using raw SQL
    failed_sessions_stmt = text("""
        SELECT id FROM sessions
        WHERE microcycle_id = ANY(:microcycle_ids)
        AND generation_status = CAST(:status AS generation_status)
    """).bindparams(bindparam("microcycle_ids"), bindparam("status"))
    result = await db.execute(
        failed_sessions_stmt,
        {"microcycle_ids": microcycle_ids, "status": GENERATION_STATUS_FAILED}
    )
    failed_session_ids = [row[0] for row in result.fetchall()]

    if not failed_session_ids:
        return {
            "program_id": program_id,
            "message": "No sessions with FAILED status found",
            "sessions_queued": 0,
        }

    # Queue regeneration
    background_tasks.add_task(
        regenerate_sessions_for_program,
        program_id=program_id,
        session_ids=failed_session_ids
    )

    logger.info(
        f"Queued regeneration of {len(failed_session_ids)} FAILED sessions "
        f"for program {program_id} (user {user_id})"
    )

    return {
        "program_id": program_id,
        "message": f"Queued regeneration of {len(failed_session_ids)} sessions",
        "sessions_queued": len(failed_session_ids),
        "session_ids": failed_session_ids,
    }


@router.post("/programs/{program_id}/generate-active-microcycle")
async def trigger_active_microcycle_generation(
    program_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Manually trigger generation for the active microcycle of a program.
    
    Use this endpoint to recover from failed background generation or
    to re-trigger generation after a server restart.
    
    Args:
        program_id: The program ID to generate sessions for
        
    Returns:
        Status message with generation queued details
    """
    # Verify program exists and user has access
    program = await db.get(Program, program_id)
    if not program:
        raise NotFoundError("Program", details={"program_id": program_id})
    if program.user_id != user_id:
        raise AuthorizationError("Not authorized to access this program")
    
    # Check active microcycle status
    result = await db.execute(
        select(Microcycle).where(
            Microcycle.program_id == program_id,
            Microcycle.status == MicrocycleStatus.ACTIVE,
        )
    )
    active_mc = result.scalar_one_or_none()
    
    if not active_mc:
        raise HTTPException(status_code=400, detail="No active microcycle found for this program")
    
    if active_mc.generation_status == GenerationStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409, 
            detail="Generation already in progress for this microcycle"
        )
    
    # Import the wrapper function from programs.py
    from app.api.routes.programs import _background_generate_sessions
    
    # Queue generation
    logger.info(
        f"[ADMIN] Manual trigger: scheduling generation for program_id={program_id}, "
        f"microcycle_id={active_mc.id}, previous_status={active_mc.generation_status}"
    )
    background_tasks.add_task(_background_generate_sessions, program_id)
    
    return {
        "program_id": program_id,
        "active_microcycle_id": active_mc.id,
        "message": "Generation queued successfully",
        "previous_status": str(active_mc.generation_status),
    }


async def regenerate_sessions_for_program(program_id: int, session_ids: List[int]):
    """
    Background task to regenerate sessions for a program.

    Properly tracks used movements and diversity state across sessions
    to ensure optimal variety in regenerated content.

    Args:
        program_id: The program ID
        session_ids: List of session IDs to regenerate
    """
    from app.db.database import async_session_maker
    from sqlalchemy.orm import selectinload

    logger.info(
        f"[REGENERATE_SESSIONS] STARTED - program_id={program_id}, "
        f"session_count={len(session_ids)}, session_ids={session_ids}"
    )

    generator = SessionGeneratorService()
    success_count = 0
    failure_count = 0

    # Initialize tracking state (same as _generate_session_content_async in program.py)
    used_movements: set[str] = set()
    used_movement_groups: dict[str, int] = {}
    used_main_patterns: dict[str, list[str]] = {}
    used_accessory_movements: dict[int, list[str]] = {}
    previous_day_volume: dict[str, int] = {}

    async with async_session_maker() as db:
        for session_id in session_ids:
            try:
                # Load session with relationships
                session_stmt = (
                    select(Session)
                    .options(selectinload(Session.microcycle))
                    .where(Session.id == session_id)
                )
                result = await db.execute(session_stmt)
                session = result.scalar_one()

                if not session.microcycle:
                    logger.error(f"[REGENERATE_SESSIONS] Session {session_id} has no microcycle, skipping")
                    failure_count += 1
                    continue

                # Load program
                program = await db.get(Program, program_id)
                if not program:
                    logger.error(f"[REGENERATE_SESSIONS] Program {program_id} not found, skipping session {session_id}")
                    failure_count += 1
                    continue

                # Regenerate session WITH tracking parameters for diversity
                logger.info(f"[REGENERATE_SESSIONS] Regenerating session {session_id} (day {session.day_number})...")
                current_volume = await generator.populate_session_by_id(
                    session_id=session_id,
                    program_id=program.id,
                    microcycle_id=session.microcycle.id,
                    used_movements=list(used_movements),
                    used_movement_groups=dict(used_movement_groups),
                    used_main_patterns=dict(used_main_patterns),
                    used_accessory_movements=dict(used_accessory_movements),
                    previous_day_volume=previous_day_volume,
                )

                # Update tracking after successful generation
                previous_day_volume = current_volume or {}

                # Re-fetch session to update used_movements tracking
                stmt = (
                    select(Session)
                    .options(selectinload(Session.exercises).selectinload(SessionExercise.movement))
                    .where(Session.id == session_id)
                )
                result = await db.execute(stmt)
                updated_session = result.scalar_one_or_none()

                if updated_session and updated_session.exercises:
                    for exercise in updated_session.exercises:
                        if exercise.movement:
                            used_movements.add(exercise.movement.name)
                            if exercise.movement.substitution_group:
                                group = exercise.movement.substitution_group
                                used_movement_groups[group] = used_movement_groups.get(group, 0) + 1

                success_count += 1
                logger.info(f"[REGENERATE_SESSIONS] Session {session_id} regenerated successfully")

            except Exception as e:
                failure_count += 1
                logger.error(f"[REGENERATE_SESSIONS] Failed to regenerate session {session_id}: {e}")
                logger.exception(e)
                # Reset volume tracking on failure to avoid cascading issues
                previous_day_volume = {}

    logger.info(
        f"[REGENERATE_SESSIONS] COMPLETED - program_id={program_id}: "
        f"{success_count} successful, {failure_count} failed"
    )
