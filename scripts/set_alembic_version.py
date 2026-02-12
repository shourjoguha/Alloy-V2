#!/usr/bin/env python3
"""
Set Alembic version to skip migrations that have already been applied.

This script sets the alembic_version to a specific revision to skip
migrations that have already been applied to the database.
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

async def set_alembic_version(target_revision):
    """Set alembic_version to a specific revision."""
    
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine)
    
    async with async_session_maker() as session:
        # Delete all existing versions
        print("Deleting all existing versions...")
        await session.execute(text("DELETE FROM alembic_version"))
        
        # Insert target version
        print(f"Setting version to '{target_revision}'...")
        await session.execute(
            text(f"INSERT INTO alembic_version (version_num) VALUES ('{target_revision}')")
        )
        await session.commit()
        
        print(f"✓ Version set to {target_revision}")
    
    await engine.dispose()

if __name__ == "__main__":
    # Set to the merge point that should exist in database
    # 38a5628f9650 is the merge_heads revision that comes before the head
    asyncio.run(set_alembic_version('38a5628f9650'))
