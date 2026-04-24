"""
钉钉对接集成测试脚本
====================
测试钉钉消息处理流程的各个环节
"""
import asyncio
import json
from app.services.llm_service import LLMService


async def test_progress_parsing():
    """测试进度解析功能"""
    print("=" * 60)
    print("测试 1: 进度解析功能")
    print("=" * 60)
    
    llm_service = LLMService()
    
    test_cases = [
        "完成了任务 A",
        "任务 B 进行中，进度 50%",
        "任务 C 遇到问题：数据库连接失败",
        "任务 D 需要延期 3 天",
        "查询任务 E 的状态"
    ]
    
    for message in test_cases:
        print(f"\n输入: {message}")
        result = await llm_service.parse_progress(message)
        print(f"输出: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("-" * 40)


async def test_simple_progress_parse():
    """测试简单的进度解析（规则引擎）"""
    print("\n" + "=" * 60)
    print("测试 2: 规则引擎进度解析")
    print("=" * 60)
    
    llm_service = LLMService()
    
    test_cases = [
        "完成了任务 A",
        "任务 B 进行中，进度 50%",
        "任务 C 遇到问题：数据库连接失败",
        "任务 D 需要延期 3 天",
    ]
    
    for message in test_cases:
        print(f"\n输入: {message}")
        result = llm_service._simple_progress_parse(message)
        print(f"输出: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("-" * 40)


async def test_task_matching():
    """测试任务匹配功能"""
    print("\n" + "=" * 60)
    print("测试 3: 任务匹配功能")
    print("=" * 60)
    
    # 模拟任务对象
    class MockTask:
        def __init__(self, id, name, description="", status="pending"):
            self.id = id
            self.name = name
            self.description = description
            self.status = status
    
    # 导入匹配函数
    from app.api.v1.dingtalk import match_tasks
    
    tasks = [
        MockTask(1, "完成用户认证", "实现用户登录功能", "in_progress"),
        MockTask(2, "数据库设计", "设计数据库表结构", "pending"),
        MockTask(3, "API 开发", "开发 REST API", "pending"),
        MockTask(4, "前端界面", "实现前端页面", "pending"),
    ]
    
    test_cases = [
        (["用户认证"], "完全匹配"),
        (["认证"], "模糊匹配"),
        (["数据库"], "关键词匹配"),
        (["不存在的任务"], "无匹配"),
    ]
    
    for keywords, description in test_cases:
        print(f"\n搜索: {keywords} ({description})")
        matched = match_tasks(tasks, keywords)
        if matched:
            for task in matched:
                print(f"  - {task.name} (ID: {task.id}, 状态: {task.status})")
        else:
            print("  无匹配结果")
        print("-" * 40)


async def main():
    """运行所有测试"""
    print("\n🧪 钉钉对接集成测试\n")
    
    try:
        # 测试 1: 进度解析（需要 LLM API）
        # await test_progress_parsing()
        
        # 测试 2: 规则引擎进度解析（不需要 API）
        await test_simple_progress_parse()
        
        # 测试 3: 任务匹配
        await test_task_matching()
        
        print("\n✅ 所有测试完成！\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
