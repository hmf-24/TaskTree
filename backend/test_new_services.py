"""
测试新实现的服务
================
测试 DingtalkUserMappingService 和 ProgressParserService
"""
import asyncio
from app.services.progress_parser_service import ProgressParserService
from app.services.llm_service import LLMService


def test_progress_parser_with_rules():
    """测试进度解析服务（规则引擎）"""
    print("=" * 60)
    print("测试进度解析服务（规则引擎）")
    print("=" * 60)
    
    # 不提供 LLM 服务，使用规则引擎
    parser = ProgressParserService()
    
    test_cases = [
        "任务 A 完成了",
        "任务 B 进行中，进度 50%",
        "任务 C 遇到问题：API 接口返回 500 错误",
        "任务 D 需要延期 3 天",
        "任务 E 的状态怎么样？",
        "完成了用户登录功能",
        "正在做数据库设计，已经完成 60%",
        "遇到 bug 了，无法连接数据库",
        "来不及了，需要推迟 5 天",
    ]
    
    for message in test_cases:
        print(f"\n消息: {message}")
        result = parser.parse(message)
        print(f"类型: {result['type']}")
        print(f"进度: {result['progress']}%")
        print(f"描述: {result['description']}")
        print(f"延期: {result['extend_days']} 天")
        print(f"置信度: {result['confidence']}")
        print(f"关键词: {result['keywords']}")


def test_progress_parser_with_llm():
    """测试进度解析服务（LLM）"""
    print("\n" + "=" * 60)
    print("测试进度解析服务（LLM）")
    print("=" * 60)
    
    # 提供 LLM 服务
    llm_service = LLMService()
    parser = ProgressParserService(llm_service)
    
    test_cases = [
        "任务 A 完成了",
        "任务 B 进行中，进度 50%",
        "任务 C 遇到问题：API 接口返回 500 错误",
    ]
    
    for message in test_cases:
        print(f"\n消息: {message}")
        try:
            result = parser.parse(message)
            print(f"类型: {result['type']}")
            print(f"进度: {result['progress']}%")
            print(f"描述: {result['description']}")
            print(f"延期: {result['extend_days']} 天")
            print(f"置信度: {result['confidence']}")
            print(f"关键词: {result['keywords']}")
        except Exception as e:
            print(f"LLM 解析失败: {e}")
            print("已降级到规则引擎")


def test_extract_methods():
    """测试提取方法"""
    print("\n" + "=" * 60)
    print("测试提取方法")
    print("=" * 60)
    
    parser = ProgressParserService()
    
    # 测试进度提取
    print("\n测试进度提取:")
    test_messages = [
        "进度 50%",
        "完成了 80%",
        "百分之 60",
        "进度：75",
    ]
    for msg in test_messages:
        progress = parser._extract_progress(msg)
        print(f"  {msg} → {progress}%")
    
    # 测试延期天数提取
    print("\n测试延期天数提取:")
    test_messages = [
        "延期 3 天",
        "推迟 5 天",
        "需要 7 天",
        "delay 2 days",
    ]
    for msg in test_messages:
        days = parser._extract_extend_days(msg)
        print(f"  {msg} → {days} 天")
    
    # 测试描述提取
    print("\n测试描述提取:")
    test_messages = [
        ("遇到问题：数据库连接失败", "problem"),
        ("任务完成了，测试通过", "completed"),
    ]
    for msg, ptype in test_messages:
        desc = parser._extract_description(msg, ptype)
        print(f"  {msg} ({ptype}) → {desc}")


if __name__ == "__main__":
    # 测试规则引擎
    test_progress_parser_with_rules()
    
    # 测试提取方法
    test_extract_methods()
    
    # 测试 LLM（如果配置了）
    # test_progress_parser_with_llm()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
