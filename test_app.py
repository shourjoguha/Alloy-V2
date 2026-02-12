import asyncio
from app.main import app
from app.db.database import async_session_maker

async def test():
    async with async_session_maker() as session:
        print('DB connection OK')
    print('App created OK')

if __name__ == "__main__":
    asyncio.run(test())
