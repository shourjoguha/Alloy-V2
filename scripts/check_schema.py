#!/usr/bin/env python3
"""
Check the current database schema to determine what migrations have been applied.
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
        # Check movements table columns
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'movements' 
            ORDER BY ordinal_position
        """))
        
        print("movements table columns:")
        for row in result:
            print(f"  - {row[0]} ({row[1]})")
        
        # Check muscles table columns
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'muscles' 
            ORDER BY ordinal_position
        """))
        
        print("\nmuscles table columns:")
        for row in result:
            print(f"  - {row[0]} ({row[1]})")
        
        # Check alembic_version
        result = await session.execute(text("SELECT * FROM alembic_version"))
        versions = result.fetchall()
        
        print(f"\nalembic_version:")
        for version in versions:
            print(f"  - {version[0]}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_schema())
