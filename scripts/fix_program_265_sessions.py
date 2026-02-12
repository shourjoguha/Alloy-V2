"""
Script to fix program 265 sessions with 0 exercises.

This script:
1. Finds all sessions for program 265 with 0 exercises and PENDING generation_status
2. Sets their generation_status to FAILED
3. Optionally regenerates those sessions
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, and_, func, text, bindparam, update
from sqlalchemy.orm import selectinload
from app.db.database import async_session_maker
from app.models import Program, Session, Microcycle, SessionExercise
from app.services.session_generator import SessionGeneratorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Generation status values as strings (matching database enum)
GENERATION_STATUS_PENDING = "pending"
GENERATION_STATUS_GENERATING = "generating"
GENERATION_STATUS_COMPLETED = "completed"
GENERATION_STATUS_FAILED = "failed"


async def count_session_exercises(session_id: int, db) -> int:
    """Count number of exercises for a given session."""
    result = await db.execute(
        select(func.count(SessionExercise.id)).where(SessionExercise.session_id == session_id)
    )
    return result.scalar() or 0


async def get_pending_sessions_with_zero_exercises(program_id: int, db) -> list[int]:
    """
    Find session IDs with PENDING status and 0 exercises for a program.
    Returns list of session IDs only to avoid enum mapping issues.
    """
    # Get all microcycle IDs for program
    microcycles_stmt = select(Microcycle.id).where(Microcycle.program_id == program_id)
    microcycle_result = await db.execute(microcycles_stmt)
    microcycle_ids = [row[0] for row in microcycle_result.fetchall()]

    if not microcycle_ids:
        return []

    # Find PENDING sessions using raw SQL with enum cast
    pending_sessions_stmt = text("""
        SELECT id FROM sessions
        WHERE microcycle_id = ANY(:microcycle_ids)
        AND generation_status = CAST(:status AS generation_status)
    """).bindparams(bindparam("microcycle_ids"), bindparam("status"))
    result = await db.execute(
        pending_sessions_stmt,
        {"microcycle_ids": microcycle_ids, "status": GENERATION_STATUS_PENDING}
    )
    pending_rows = result.fetchall()

    # Filter sessions with 0 exercises
    sessions_with_zero_exercises = []
    for row in pending_rows:
        session_id = row[0]
        exercise_count = await count_session_exercises(session_id, db)
        if exercise_count == 0:
            sessions_with_zero_exercises.append(session_id)
            logger.info(f"Session {session_id} has {exercise_count} exercises")

    return sessions_with_zero_exercises


async def fix_program_265_sessions(regenerate: bool = False):
    """
    Fix sessions for program 265.

    Args:
        regenerate: If True, regenerate sessions after marking them as FAILED
    """
    PROGRAM_ID = 265

    async with async_session_maker() as db:
        # Find all sessions for program 265
        logger.info(f"Finding all sessions for program {PROGRAM_ID}...")

        # First, get microcycle info
        microcycles_stmt = select(Microcycle.id).where(Microcycle.program_id == PROGRAM_ID)
        microcycle_result = await db.execute(microcycles_stmt)
        microcycle_ids = [row[0] for row in microcycle_result.fetchall()]

        if not microcycle_ids:
            logger.error(f"No microcycles found for program {PROGRAM_ID}")
            return

        logger.info(f"Found {len(microcycle_ids)} microcycles for program {PROGRAM_ID}")

        # Get session IDs with 0 exercises and PENDING status
        session_ids_to_fix = await get_pending_sessions_with_zero_exercises(PROGRAM_ID, db)

        logger.info(
            f"Found {len(session_ids_to_fix)} sessions with 0 exercises and PENDING status"
        )

        if not session_ids_to_fix:
            logger.info("No sessions need to be fixed.")
            return

        # Set generation_status to FAILED using direct UPDATE statement
        update_stmt = text("""
            UPDATE sessions
            SET generation_status = CAST(:new_status AS generation_status)
            WHERE id = ANY(:session_ids)
            AND generation_status = CAST(:old_status AS generation_status)
        """).bindparams(
            bindparam("new_status"),
            bindparam("session_ids"),
            bindparam("old_status")
        )
        result = await db.execute(
            update_stmt,
            {
                "new_status": GENERATION_STATUS_FAILED,
                "session_ids": session_ids_to_fix,
                "old_status": GENERATION_STATUS_PENDING
            }
        )

        updated_count = result.rowcount
        await db.commit()
        logger.info(f"Successfully marked {updated_count} sessions as FAILED")

        # Optionally regenerate sessions
        if regenerate:
            logger.info("Starting session regeneration...")
            generator = SessionGeneratorService()

            # Load program once
            program = await db.get(Program, PROGRAM_ID)
            if not program:
                logger.error(f"Program {PROGRAM_ID} not found")
                return

            for session_id in session_ids_to_fix:
                # Load session with relationships
                session_stmt = (
                    select(Session)
                    .options(selectinload(Session.microcycle))
                    .where(Session.id == session_id)
                )
                result = await db.execute(session_stmt)
                session = result.scalar_one_or_none()

                if not session:
                    logger.error(f"Session {session_id} not found")
                    continue

                if not session.microcycle:
                    logger.error(f"Session {session_id} has no microcycle")
                    continue

                # Reload the session with fresh data
                await db.refresh(session)

                logger.info(f"Regenerating session {session_id}...")

                try:
                    result = await generator.populate_session_by_id(
                        session_id=session.id,
                        program_id=program.id,
                        microcycle_id=session.microcycle.id
                    )
                    logger.info(f"Session {session_id} regenerated successfully: {result}")
                except Exception as e:
                    logger.error(f"Failed to regenerate session {session_id}: {e}")
                    logger.exception(e)

            logger.info("Session regeneration completed")


async def summarize_program_265():
    """Provide a summary of program 265 sessions."""
    PROGRAM_ID = 265

    async with async_session_maker() as db:
        # Get program info
        program = await db.get(Program, PROGRAM_ID)
        if not program:
            logger.error(f"Program {PROGRAM_ID} not found")
            return

        logger.info(f"=== Program {PROGRAM_ID} Summary ===")
        logger.info(f"Name: {program.name}")
        logger.info(f"User ID: {program.user_id}")
        logger.info(f"Start Date: {program.start_date}")
        logger.info(f"Duration: {program.duration_weeks} weeks")
        logger.info(f"Split: {program.split_template}")

        # Get microcycles
        microcycles_stmt = select(Microcycle).where(Microcycle.program_id == PROGRAM_ID)
        microcycles_result = await db.execute(microcycles_stmt)
        microcycles = microcycles_result.scalars().all()

        logger.info(f"Microcycles: {len(microcycles)}")

        # Get session counts by generation_status using raw SQL
        microcycle_ids = [m.id for m in microcycles]

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
            logger.info(f"Sessions with {status_name} status: {count}")

        # Count sessions with 0 exercises by status
        logger.info("\n=== Sessions with 0 exercises by status ===")
        for status_name, status_value in [
            ("PENDING", GENERATION_STATUS_PENDING),
            ("GENERATING", GENERATION_STATUS_GENERATING),
            ("COMPLETED", GENERATION_STATUS_COMPLETED),
            ("FAILED", GENERATION_STATUS_FAILED),
        ]:
            sessions_stmt = text("""
                SELECT id, date, session_type FROM sessions
                WHERE microcycle_id = ANY(:microcycle_ids)
                AND generation_status = CAST(:status AS generation_status)
            """).bindparams(bindparam("microcycle_ids"), bindparam("status"))
            result = await db.execute(
                sessions_stmt,
                {"microcycle_ids": microcycle_ids, "status": status_value}
            )
            sessions = result.fetchall()

            zero_exercise_count = 0
            for session_id, date, session_type in sessions:
                exercise_count = await count_session_exercises(session_id, db)
                if exercise_count == 0:
                    zero_exercise_count += 1

            if zero_exercise_count > 0:
                logger.info(f"{status_name}: {zero_exercise_count} sessions with 0 exercises")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix program 265 sessions")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate sessions after marking them as FAILED"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show summary, don't make changes"
    )
    args = parser.parse_args()

    if args.summary_only:
        asyncio.run(summarize_program_265())
    else:
        asyncio.run(fix_program_265_sessions(regenerate=args.regenerate))
