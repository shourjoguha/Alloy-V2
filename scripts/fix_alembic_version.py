#!/usr/bin/env python3
"""
Fix Alembic version by cleaning up duplicate entries and updating to a valid revision.

This script updates the alembic_version table to a valid revision
when database contains a stale/missing revision ID.
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

async def fix_alembic_version():
    """Fix the alembic_version table by setting it to a valid revision."""
    
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine)
    
    async with async_session_maker() as session:
        # Check all versions in the table
        result = await session.execute(text("SELECT * FROM alembic_version"))
        all_versions = result.fetchall()
        
        print(f"Found {len(all_versions)} version(s) in alembic_version table:")
        for version in all_versions:
            print(f"  - {version[0]}")
        
        # Delete all existing versions
        print("\nDeleting all existing versions...")
        await session.execute(text("DELETE FROM alembic_version"))
        
        # Insert the correct version (d85b37d662b7 is phase2_step1_drop_muscles_name_column)
        # This is a valid revision that should exist
        print("Inserting valid revision 'd85b37d662b7'...")
        await session.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('d85b37d662b7')")
        )
        await session.commit()
        
        print("✓ Fixed successfully!")
        print("\nYou can now run: alembic upgrade head")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_alembic_version())
