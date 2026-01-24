"""
Integration test for program creation with LLM session generation.
"""
import asyncio
import sys
from datetime import date

sys.path.insert(0, '/Users/shourjosmac/Documents/Gainsly')

from sqlalchemy import select
from app.db.database import async_session_maker
from app.models import Program, Microcycle, Session, User, Movement
from app.models.enums import Goal, SplitTemplate, ProgressionStyle
from app.schemas.program import ProgramCreate, GoalWeight
from app.services.program import program_service


async def test_program_creation():
    """Test full program creation with LLM session generation."""
    print("🧪 Testing program creation with LLM integration...\n")
    
    async with async_session_maker() as db:
        # Check movements exist
        movements_result = await db.execute(select(Movement))
        movements = movements_result.scalars().all()
        print(f"✓ Found {len(movements)} movements in database")
        
        if len(movements) == 0:
            print("❌ No movements found! Run seed data first.")
            return False
        
        # Check user exists
        user_result = await db.execute(select(User).where(User.id == 1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("❌ Default user (id=1) not found! Run seed data first.")
            return False
        
        print(f"✓ Found user: {user.name}\n")
        
        # Create test program
        print("Creating test program...")
        program_data = ProgramCreate(
                goals=[
                    GoalWeight(goal=Goal.STRENGTH, weight=5),
                    GoalWeight(goal=Goal.HYPERTROPHY, weight=3),
                    GoalWeight(goal=Goal.ENDURANCE, weight=2),
                ],
                duration_weeks=8,
                split_template=SplitTemplate.UPPER_LOWER,
                days_per_week=4,
                progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
                program_start_date=date.today(),
            )
        
        try:
            program = await program_service.create_program(db, user_id=1, request=program_data)
            print(f"✓ Program created: ID={program.id}")
            
            # Check microcycles
            microcycles_result = await db.execute(
                select(Microcycle).where(Microcycle.program_id == program.id)
            )
            microcycles = microcycles_result.scalars().all()
            print(f"✓ Created {len(microcycles)} microcycles")
            
            # Check sessions
            sessions_result = await db.execute(
                select(Session).where(Session.microcycle_id == microcycles[0].id)
            )
            sessions = sessions_result.scalars().all()
            print(f"✓ Created {len(sessions)} sessions in first microcycle")
            
            # Check if sessions have exercises (LLM generated content)
            sessions_with_exercises = 0
            for session in sessions:
                if session.main_json and len(session.main_json) > 0:
                    sessions_with_exercises += 1
                    print(f"  • Session {session.day_number} ({session.session_type.value}): {len(session.main_json)} main exercises")
                    if session.coach_notes:
                        print(f"    Notes: {session.coach_notes[:80]}...")
            
            print(f"\n✓ {sessions_with_exercises}/{len(sessions)} sessions have LLM-generated exercises")
            
            if sessions_with_exercises == 0:
                print("⚠️  WARNING: No sessions have exercises! LLM generation may have failed.")
                return False
            
            print("\n✅ Integration test PASSED!")
            print(f"\nProgram Summary:")
            print(f"- ID: {program.id}")
            print(f"- Goals: {program.goal_1.value} ({program.goal_weight_1}), {program.goal_2.value} ({program.goal_weight_2}), {program.goal_3.value} ({program.goal_weight_3})")
            print(f"- Split: {program.split_template.value}")
            print(f"- Duration: {program.duration_weeks} weeks")
            print(f"- Sessions with exercises: {sessions_with_exercises}/{len(sessions)}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(test_program_creation())
    sys.exit(0 if success else 1)
