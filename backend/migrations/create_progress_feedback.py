"""
数据库迁移脚本：创建进度反馈表
================================
创建 progress_feedback 表用于记录用户通过钉钉发送的进度反馈
"""
import asyncio
from sqlalchemy import text
from app.core.database import get_engine


async def migrate_up():
    """执行迁移"""
    engine = get_engine()
    async with engine.begin() as conn:
        # 创建 progress_feedback 表
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS progress_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                message_content TEXT NOT NULL,
                parsed_result TEXT,
                feedback_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """)
        )
        print("✓ 创建 progress_feedback 表")
        
        # 创建索引
        try:
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_progress_feedback_user_id 
                ON progress_feedback(user_id)
                """)
            )
            print("✓ 创建 user_id 索引")
        except:
            pass
        
        try:
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_progress_feedback_task_id 
                ON progress_feedback(task_id)
                """)
            )
            print("✓ 创建 task_id 索引")
        except:
            pass
        
        try:
            await conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_progress_feedback_created_at 
                ON progress_feedback(created_at)
                """)
            )
            print("✓ 创建 created_at 索引")
        except:
            pass


async def migrate_down():
    """回滚迁移"""
    engine = get_engine()
    async with engine.begin() as conn:
        # 删除索引
        try:
            await conn.execute(
                text("DROP INDEX IF EXISTS idx_progress_feedback_user_id")
            )
            print("✓ 删除 user_id 索引")
        except:
            pass
        
        try:
            await conn.execute(
                text("DROP INDEX IF EXISTS idx_progress_feedback_task_id")
            )
            print("✓ 删除 task_id 索引")
        except:
            pass
        
        try:
            await conn.execute(
                text("DROP INDEX IF EXISTS idx_progress_feedback_created_at")
            )
            print("✓ 删除 created_at 索引")
        except:
            pass
        
        # 删除表
        try:
            await conn.execute(
                text("DROP TABLE IF EXISTS progress_feedback")
            )
            print("✓ 删除 progress_feedback 表")
        except:
            pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        asyncio.run(migrate_down())
    else:
        asyncio.run(migrate_up())
