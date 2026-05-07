import asyncio
from sqlalchemy import text
from app.core.database import get_db

async def test():
    async for db in get_db():
        result = await db.execute(text("PRAGMA foreign_keys"))
        fk_status = result.fetchone()[0]
        print(f"FK status in app: {fk_status}")
        break

asyncio.run(test())
