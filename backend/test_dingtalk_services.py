"""
钉钉智能助手服务测试脚本
========================
测试 TaskMatcherService 和 TaskUpdaterService
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_session_maker
from app.services.task_matcher import TaskMatcherService
from app.services.task_updater import TaskUpdaterService
from app.schemas import ParseResultSchema
from sqlalchemy import select
from app.models import User, Task, Project


async def test_task_matcher():
    """测试任务匹配服务"""
    print("\n=== 测试 TaskMatcherService ===\n")
    
    async with get_session_maker()() as db:
        # 获取第一个用户
        result = await db.execute(select(User).limit(1))
        user = result.scalars().first()
        
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return
        
        print(f"✓ 使用用户: {user.email} (ID: {user.id})")
        
        # 创建 TaskMatcherService
        matcher = TaskMatcherService(db)
        
        # 测试匹配
        keywords = ["测试", "任务"]
        print(f"\n搜索关键词: {keywords}")
        
        matched_tasks = await matcher.match(
            keywords=keywords,
            user_id=user.id,
            limit=5
        )
        
        if matched_tasks:
            print(f"\n✓ 找到 {len(matched_tasks)} 个匹配的任务:")
            for i, task in enumerate(matched_tasks, 1):
                print(f"  {i}. {task.name} (状态: {task.status}, 进度: {task.progress}%)")
        else:
            print("\n⚠ 没有找到匹配的任务")
        
        # 测试带分数的匹配
        print(f"\n搜索关键词（带分数）: {keywords}")
        scored_tasks = await matcher.match_with_scores(
            keywords=keywords,
            user_id=user.id,
            limit=5
        )
        
        if scored_tasks:
            print(f"\n✓ 找到 {len(scored_tasks)} 个匹配的任务（带分数）:")
            for i, (task, score) in enumerate(scored_tasks, 1):
                print(f"  {i}. {task.name} - 分数: {score}")
        else:
            print("\n⚠ 没有找到匹配的任务")


async def test_task_updater():
    """测试任务更新服务"""
    print("\n=== 测试 TaskUpdaterService ===\n")
    
    async with get_session_maker()() as db:
        # 获取第一个用户
        result = await db.execute(select(User).limit(1))
        user = result.scalars().first()
        
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return
        
        print(f"✓ 使用用户: {user.email} (ID: {user.id})")
        
        # 获取第一个任务
        result = await db.execute(
            select(Task).join(Project).where(
                Project.owner_id == user.id
            ).limit(1)
        )
        task = result.scalars().first()
        
        if not task:
            print("❌ 没有找到任务，请先创建任务")
            return
        
        print(f"✓ 使用任务: {task.name} (ID: {task.id})")
        print(f"  当前状态: {task.status}, 进度: {task.progress}%")
        
        # 创建 TaskUpdaterService
        updater = TaskUpdaterService(db)
        
        # 测试更新任务（模拟进度反馈）
        parse_result = ParseResultSchema(
            progress_type="in_progress",
            confidence=0.95,
            keywords=[task.name],
            progress_value=50,
            problem_description="",
            extend_days=0,
            raw_message=f"任务 {task.name} 进行中，进度 50%"
        )
        
        print(f"\n模拟进度反馈: {parse_result.raw_message}")
        
        try:
            updated_task = await updater.update_from_feedback(
                task_id=task.id,
                parse_result=parse_result,
                user_id=user.id,
                message_content=parse_result.raw_message
            )
            
            print(f"\n✓ 任务更新成功!")
            print(f"  新状态: {updated_task.status}, 新进度: {updated_task.progress}%")
        
        except PermissionError as e:
            print(f"\n❌ 权限错误: {e}")
        except ValueError as e:
            print(f"\n❌ 值错误: {e}")
        except Exception as e:
            print(f"\n❌ 更新失败: {e}")


async def main():
    """主函数"""
    print("=" * 60)
    print("钉钉智能助手服务测试")
    print("=" * 60)
    
    try:
        await test_task_matcher()
        await test_task_updater()
        
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
