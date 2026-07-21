import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT status, count(*) FROM incidents GROUP BY status"))
        for row in res:
            print(row)
        res = await conn.execute(text("SELECT id, restricted FROM incidents LIMIT 5"))
        for row in res:
            print(row)
asyncio.run(check())
