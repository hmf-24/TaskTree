"""检查用户头像"""
import asyncio
from sqlalchemy import select
from app.core.database import get_session_maker
from app.models import User

async def check_avatar():
    session_maker = get_session_maker()
    async with session_maker() as db:
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        if user:
            print(f"用户ID: {user.id}")
            print(f"邮箱: {user.email}")
            print(f"昵称: {user.nickname}")
            print(f"头像URL: {user.avatar}")
        else:
            print("用户不存在")

if __name__ == "__main__":
    asyncio.run(check_avatar())
