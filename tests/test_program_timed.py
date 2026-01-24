"""Test program creation with timing."""
import asyncio
import sys
import time
sys.path.insert(0, '/Users/shourjosmac/Documents/Gainsly')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.enums import Goal, SplitTemplate, ProgressionStyle
from app.schemas.program import ProgramCreate, GoalWeight, DisciplineWeight
from app.services.program import program_service

async def test_program_creation():
    """Test creating a program with 4 days and CrossFit."""
    print("=== Testing Program Creation with 1100s timeout ===\n")
    
    # Setup database connection
    engine = create_async_engine(
        "sqlite+aiosqlite:///workout_coach.db",
        echo=False,
    )
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as db:
        try:
            # Create program request
            request = ProgramCreate(
                goals=[
                    GoalWeight(goal=Goal.STRENGTH, weight=5),
                    GoalWeight(goal=Goal.EXPLOSIVENESS, weight=3),
                    GoalWeight(goal=Goal.SPEED, weight=2),
                ],
                duration_weeks=12,
                split_template=SplitTemplate.FULL_BODY,
                days_per_week=4,
                progression_style=ProgressionStyle.DOUBLE_PROGRESSION,
                disciplines=[
                    DisciplineWeight(discipline="crossfit", weight=5),
                    DisciplineWeight(discipline="powerlifting", weight=5),
                ],
            )
            
            print(f"Request: 4 days/week, Full Body, CrossFit + Powerlifting")
            print(f"Timeout: 1100 seconds (18+ minutes)\n")
            
            start = time.time()
            print(f"[{time.strftime('%H:%M:%S')}] Starting program creation...")
            
            # Create program
            program = await program_service.create_program(db, user_id=1, request=request)
            
            elapsed = time.time() - start
            print(f"[{time.strftime('%H:%M:%S')}] ✓ Program created in {elapsed:.1f}s")
            print(f"\nProgram ID: {program.id}")
            print(f"Days per week: {program.days_per_week}")

            # Check disciplines
            await db.refresh(program, ["program_disciplines"])
            if program.program_disciplines:
                print(f"Disciplines: {[(pd.discipline_type, pd.weight) for pd in program.program_disciplines]}")

            # Check sessions
            await db.refresh(program, ["microcycles"])
            if program.microcycles:
                active_mc = next((mc for mc in program.microcycles if mc.status.value == "active"), None)
                if active_mc:
                    await db.refresh(active_mc, ["sessions"])
                    
                    training_sessions = [s for s in active_mc.sessions if s.session_type.value != "recovery"]
                    print(f"\nTraining sessions: {len(training_sessions)}")
                    
                    complete_count = 0
                    for session in training_sessions:
                        has_warmup = session.warmup_json and len(session.warmup_json) > 0
                        has_main = session.main_json and len(session.main_json) > 0
                        has_cooldown = session.cooldown_json and len(session.cooldown_json) > 0
                        has_finisher = session.finisher_json is not None
                        
                        is_complete = has_warmup and has_main and has_cooldown and (session.accessory_json or has_finisher)
                        if is_complete:
                            complete_count += 1
                        
                        status = "✓ COMPLETE" if is_complete else "✗ INCOMPLETE"
                        print(f"\nDay {session.day_number} ({session.session_type.value}): {status}")
                        print(f"  Warmup: {'✓' if has_warmup else '✗'}")
                        
                        if has_main:
                            print(f"  Main: ✓ ({len(session.main_json)} exercises)")
                            for ex in session.main_json:
                                print(f"    - {ex.get('movement')}")
                        else:
                            print(f"  Main: ✗")
                            
                        if session.accessory_json:
                            print(f"  Accessory: ✓ ({len(session.accessory_json)} exercises)")
                            for ex in session.accessory_json:
                                superset = f" (Superset with: {ex.get('superset_with')})" if ex.get('superset_with') else ""
                                print(f"    - {ex.get('movement')}{superset}")
                        else:
                            print(f"  Accessory: ✗")
                            
                        if has_finisher:
                            print(f"  Finisher: ✓ ({session.finisher_json.get('type', 'Unknown')})")
                            if session.finisher_json.get('exercises'):
                                for ex in session.finisher_json['exercises']:
                                    print(f"    - {ex.get('movement')}")
                        else:
                            print(f"  Finisher: ✗")
                            
                        print(f"  Cooldown: {'✓' if has_cooldown else '✗'}")
                    print(f"SUCCESS CRITERIA:")
                    print(f"  ✓ User's 4 days/week respected: {len(training_sessions) == 4}")
                    print(f"  ✓ All sessions complete: {complete_count == len(training_sessions)}")
                    print(f"  ✓ Disciplines stored: {program.program_disciplines is not None and len(program.program_disciplines) > 0}")
            
        except Exception as e:
            elapsed = time.time() - start
            print(f"\n[{time.strftime('%H:%M:%S')}] ✗ Error after {elapsed:.1f}s: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_program_creation())
