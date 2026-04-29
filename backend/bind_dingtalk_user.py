"""
手动绑定钉钉用户ID
"""
import asyncio
from app.core.database import get_session_maker
from app.models import UserNotificationSettings
from sqlalchemy import select, update

async def bind_dingtalk_user():
    """绑定钉钉用户ID到用户账号"""
    user_id = 1  # 你的用户ID
    dingtalk_user_id = "manager5045"  # 你的钉钉用户ID
    dingtalk_name = "HMF"  # 你的钉钉昵称
    
    session_maker = get_session_maker()
    async with session_maker() as db:
        # 查询用户设置
        result = await db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.user_id == user_id
            )
        )
        settings = result.scalar_one_or_none()
        
        if settings:
            # 更新钉钉用户ID
            settings.dingtalk_user_id = dingtalk_user_id
            settings.dingtalk_name = dingtalk_name
            await db.commit()
            print(f"✅ 成功绑定钉钉用户ID: {dingtalk_user_id}")
            print(f"   用户ID: {user_id}")
            print(f"   钉钉昵称: {dingtalk_name}")
        else:
            print(f"❌ 未找到用户 {user_id} 的通知设置")

if __name__ == "__main__":
    asyncio.run(bind_dingtalk_user())
