"""Test program creation with user preferences."""
import asyncio
import sys
sys.path.insert(0, '/Users/shourjosmac/Documents/Gainsly')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.enums import Goal, SplitTemplate, ProgressionStyle
from app.schemas.program import ProgramCreate, GoalWeight, DisciplineWeight
from app.services.program import program_service

async def test_program_creation():
    """Test creating a program with 4 days and CrossFit."""
    print("=== Testing Program Creation ===")
    
    # Setup database connection
    engine = create_async_engine(
        "sqlite+aiosqlite:///workout_coach.db",
        echo=False,
    )
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as db:
        try:
            # Create program request with all preferences
            request = ProgramCreate(
                goals=[
                    GoalWeight(goal=Goal.STRENGTH, weight=5),
                    GoalWeight(goal=Goal.EXPLOSIVENESS, weight=3),
                    GoalWeight(goal=Goal.SPEED, weight=2),
                ],
                duration_weeks=12,
                split_template=SplitTemplate.FULL_BODY,
                days_per_week=4,  # User wants 4 days
                progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
                disciplines=[
                    DisciplineWeight(discipline="crossfit", weight=5),
                    DisciplineWeight(discipline="powerlifting", weight=5),
                ],
            )
            
            print(f"Creating program with:")
            print(f"  - Goals: {[f'{g.goal.value}({g.weight})' for g in request.goals]}")
            print(f"  - Days per week: {request.days_per_week}")
            print(f"  - Disciplines: {[(d.discipline, d.weight) for d in request.disciplines]}")
            print(f"  - Split: {request.split_template.value}")
            
            # Create program
            user_id = 1
            program = await program_service.create_program(db, user_id, request)
            
            print(f"\n✓ Program created successfully!")
            print(f"  - Program ID: {program.id}")
            print(f"  - Days per week (stored): {program.days_per_week}")

            # Check microcycles and sessions
            await db.refresh(program, ["microcycles", "program_disciplines"])
            if program.program_disciplines:
                print(f"  - Disciplines (stored): {[(pd.discipline_type, pd.weight) for pd in program.program_disciplines]}")
            if program.microcycles:
                active_mc = next((mc for mc in program.microcycles if mc.status.value == "active"), None)
                if active_mc:
                    await db.refresh(active_mc, ["sessions"])
                    print(f"  - Active microcycle: {active_mc.id} with {len(active_mc.sessions)} sessions")
                    
                    training_sessions = [s for s in active_mc.sessions if s.session_type.value != "recovery"]
                    print(f"  - Training sessions: {len(training_sessions)}")
                    
                    for session in training_sessions[:3]:  # Check first 3
                        has_warmup = session.warmup_json is not None and len(session.warmup_json) > 0
                        has_main = session.main_json is not None and len(session.main_json) > 0
                        has_cooldown = session.cooldown_json is not None and len(session.cooldown_json) > 0
                        has_finisher = session.finisher_json is not None
                        
                        print(f"\n  Session Day {session.day_number} ({session.session_type.value}):")
                        print(f"    Warmup: {'✓' if has_warmup else '✗'}")
                        print(f"    Main: {'✓' if has_main else '✗'}")
                        print(f"    Finisher: {'✓' if has_finisher else '✗'}")
                        print(f"    Cooldown: {'✓' if has_cooldown else '✗'}")
                        
                        if has_main and session.main_json:
                            print(f"    Main exercises: {[ex.get('movement', 'Unknown') for ex in session.main_json[:2]]}")
            
        except Exception as e:
            print(f"\n✗ Error creating program: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_program_creation())
