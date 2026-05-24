"""
数据库迁移脚本：Task DAG 与元数据升级
=====================================
为 tasks 表添加 metadata_json 和 task_type 字段。
为 task_dependencies 表添加 dependency_type 字段。
"""
import asyncio
from sqlalchemy import text
from app.core.database import get_engine


async def migrate_up():
    """执行迁移"""
    engine = get_engine()
    async with engine.begin() as conn:
        # ── tasks 表：添加 metadata_json 字段 ──
        try:
            await conn.execute(
                text("ALTER TABLE tasks ADD COLUMN metadata_json TEXT")
            )
            print("✓ tasks 表添加 metadata_json 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠ metadata_json 字段已存在，跳过")
            else:
                print(f"⚠ 添加 metadata_json 字段警告: {e}")

        # ── tasks 表：添加 task_type 字段 ──
        try:
            await conn.execute(
                text("ALTER TABLE tasks ADD COLUMN task_type VARCHAR(20) DEFAULT 'manual'")
            )
            print("✓ tasks 表添加 task_type 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠ task_type 字段已存在，跳过")
            else:
                print(f"⚠ 添加 task_type 字段警告: {e}")

        # ── task_dependencies 表：添加 dependency_type 字段 ──
        try:
            await conn.execute(
                text("ALTER TABLE task_dependencies ADD COLUMN dependency_type VARCHAR(30) DEFAULT 'finish_to_start'")
            )
            print("✓ task_dependencies 表添加 dependency_type 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠ dependency_type 字段已存在，跳过")
            else:
                print(f"⚠ 添加 dependency_type 字段警告: {e}")

        print("\n✅ DAG 与元数据迁移完成")


async def migrate_down():
    """回滚迁移
    注意：SQLite 不支持 DROP COLUMN（3.35.0 之前的版本）。
    如需回滚，可能需要重建表。这里仅尝试执行。
    """
    engine = get_engine()
    async with engine.begin() as conn:
        for table, column in [
            ("tasks", "metadata_json"),
            ("tasks", "task_type"),
            ("task_dependencies", "dependency_type"),
        ]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} DROP COLUMN {column}")
                )
                print(f"✓ {table} 表删除 {column} 字段")
            except Exception as e:
                print(f"⚠ 删除 {table}.{column} 失败: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        asyncio.run(migrate_down())
    else:
        asyncio.run(migrate_up())
