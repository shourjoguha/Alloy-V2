#!/usr/bin/env python3
"""
Check the current user_profiles table schema.
"""
import asyncio
import os
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Add project root to Python path
project_root = Path(__file__).parent.parent
os.chdir(project_root)

# Database connection (same as in settings)
DATABASE_URL = "postgresql+asyncpg://gainsly:gainslypass@localhost:5433/gainslydb"

async def check_schema():
    """Check current database schema."""
    
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine)
    
    async with async_session_maker() as session:
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_profiles' 
            ORDER BY ordinal_position
        """))
        
        print("user_profiles table columns:")
        for row in result:
            print(f"  - {row[0]} ({row[1]})")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_schema())
