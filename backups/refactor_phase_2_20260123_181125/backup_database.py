import sys
import os
sys.path.insert(0, '/Users/shourjosmac/Documents/Gainsly')

import asyncio
from sqlalchemy import text
from app.db.database import async_session_maker

async def backup_database():
    async with async_session_maker() as session:
        async with session.begin():
            result = await session.execute(text("SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
            tables = result.fetchall()
            
            print(f"Found {len(tables)} tables in public schema")
            
            with open('backups/refactor_phase_2_20260123_181125/table_counts.txt', 'w') as f:
                for schema, table in tables:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM public.\"{table}\""))
                    count = result.scalar()
                    f.write(f"{table}: {count} rows\n")
                    print(f"  {table}: {count} rows")
            
            print("Database backup completed: table counts saved to table_counts.txt")

if __name__ == "__main__":
    asyncio.run(backup_database())
