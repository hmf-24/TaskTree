"""
添加钉钉Stream模式配置字段
"""
import asyncio
from sqlalchemy import text
from app.core.database import get_session_maker


async def migrate():
    """添加钉钉Stream配置字段到user_notification_settings表"""
    session_maker = get_session_maker()
    async with session_maker() as db:
        try:
            # 添加钉钉Stream配置字段
            await db.execute(text("""
                ALTER TABLE user_notification_settings 
                ADD COLUMN dingtalk_client_id VARCHAR(100) DEFAULT NULL
            """))
            print("✓ 添加 dingtalk_client_id 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  dingtalk_client_id 字段已存在")
            else:
                print(f"⚠️  添加 dingtalk_client_id 字段失败: {e}")

        try:
            await db.execute(text("""
                ALTER TABLE user_notification_settings 
                ADD COLUMN dingtalk_client_secret_encrypted TEXT DEFAULT NULL
            """))
            print("✓ 添加 dingtalk_client_secret_encrypted 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  dingtalk_client_secret_encrypted 字段已存在")
            else:
                print(f"⚠️  添加 dingtalk_client_secret_encrypted 字段失败: {e}")

        try:
            await db.execute(text("""
                ALTER TABLE user_notification_settings 
                ADD COLUMN dingtalk_stream_enabled BOOLEAN DEFAULT 0
            """))
            print("✓ 添加 dingtalk_stream_enabled 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  dingtalk_stream_enabled 字段已存在")
            else:
                print(f"⚠️  添加 dingtalk_stream_enabled 字段失败: {e}")

        await db.commit()
        print("✅ 数据库迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate())
