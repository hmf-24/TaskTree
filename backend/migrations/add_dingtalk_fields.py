"""
数据库迁移脚本：添加钉钉相关字段
================================
为 user_notification_settings 表添加钉钉用户 ID 和名称字段
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def migrate_up():
    """执行迁移"""
    async with engine.begin() as conn:
        # 检查字段是否已存在
        result = await conn.execute(
            text("PRAGMA table_info(user_notification_settings)")
        )
        columns = {row[1] for row in result.fetchall()}
        
        # 添加 dingtalk_user_id 字段
        if 'dingtalk_user_id' not in columns:
            await conn.execute(
                text("""
                ALTER TABLE user_notification_settings 
                ADD COLUMN dingtalk_user_id VARCHAR(100) UNIQUE
                """)
            )
            print("✓ 添加 dingtalk_user_id 字段")
        
        # 添加 dingtalk_name 字段
        if 'dingtalk_name' not in columns:
            await conn.execute(
                text("""
                ALTER TABLE user_notification_settings 
                ADD COLUMN dingtalk_name VARCHAR(100)
                """)
            )
            print("✓ 添加 dingtalk_name 字段")
        
        # 创建索引
        try:
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_dingtalk_user_id 
                ON user_notification_settings(dingtalk_user_id)
                """)
            )
            print("✓ 创建 dingtalk_user_id 索引")
        except:
            pass


async def migrate_down():
    """回滚迁移"""
    async with engine.begin() as conn:
        # 删除索引
        try:
            await conn.execute(
                text("DROP INDEX IF EXISTS idx_dingtalk_user_id")
            )
            print("✓ 删除 dingtalk_user_id 索引")
        except:
            pass
        
        # 删除字段（SQLite 不支持 DROP COLUMN，需要重建表）
        print("⚠ SQLite 不支持直接删除列，需要手动处理")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        asyncio.run(migrate_down())
    else:
        asyncio.run(migrate_up())
