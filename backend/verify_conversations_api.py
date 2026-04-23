"""
验证 Conversations API 端点
============================
这个脚本用于验证所有 API 端点是否正确注册和配置
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app


def verify_api_endpoints():
    """验证 API 端点"""
    print("=" * 60)
    print("验证 Conversations API 端点")
    print("=" * 60)
    
    # 查找所有对话相关的路由
    conversation_routes = [
        route for route in app.routes
        if hasattr(route, 'path') and '/conversations' in route.path
    ]
    
    print(f"\n找到 {len(conversation_routes)} 个对话相关路由:\n")
    
    expected_endpoints = {
        ('POST', '/api/v1/tasktree/conversations'): '创建新对话',
        ('POST', '/api/v1/tasktree/conversations/{conversation_id}/messages'): '发送消息',
        ('GET', '/api/v1/tasktree/conversations'): '获取对话列表',
        ('GET', '/api/v1/tasktree/conversations/{conversation_id}'): '获取对话详情',
        ('POST', '/api/v1/tasktree/conversations/{conversation_id}/analyze'): '任务分析',
        ('POST', '/api/v1/tasktree/conversations/{conversation_id}/modify'): '任务修改',
        ('POST', '/api/v1/tasktree/conversations/{conversation_id}/plan'): '项目规划',
        ('DELETE', '/api/v1/tasktree/conversations/{conversation_id}'): '删除对话',
    }
    
    found_endpoints = {}
    for route in conversation_routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            for method in route.methods:
                if method != 'HEAD':  # 忽略 HEAD 方法
                    key = (method, route.path)
                    found_endpoints[key] = True
                    desc = expected_endpoints.get(key, '未知')
                    print(f"  ✓ {method:6} {route.path:60} - {desc}")
    
    # 检查是否所有预期端点都已注册
    print(f"\n{'=' * 60}")
    print("验证结果:")
    print("=" * 60)
    
    missing = []
    for endpoint, desc in expected_endpoints.items():
        if endpoint not in found_endpoints:
            missing.append((endpoint, desc))
    
    if missing:
        print("\n❌ 缺失的端点:")
        for (method, path), desc in missing:
            print(f"  - {method} {path} - {desc}")
        return False
    else:
        print("\n✅ 所有 API 端点已正确注册!")
        print(f"\n总计: {len(expected_endpoints)} 个端点")
        return True


def verify_services():
    """验证服务类是否可以导入"""
    print("\n" + "=" * 60)
    print("验证服务类导入")
    print("=" * 60 + "\n")
    
    services = [
        ('app.services.ai_conversation_service', 'AIConversationService'),
        ('app.services.task_analyzer', 'TaskAnalyzer'),
        ('app.services.task_modifier', 'TaskModifier'),
        ('app.services.project_planner', 'ProjectPlanner'),
        ('app.services.llm_service', 'LLMService'),
    ]
    
    all_ok = True
    for module_name, class_name in services:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✓ {class_name:30} - 导入成功")
        except Exception as e:
            print(f"  ❌ {class_name:30} - 导入失败: {e}")
            all_ok = False
    
    if all_ok:
        print("\n✅ 所有服务类导入成功!")
    else:
        print("\n❌ 部分服务类导入失败!")
    
    return all_ok


def verify_schemas():
    """验证 Schemas 是否正确定义"""
    print("\n" + "=" * 60)
    print("验证 Pydantic Schemas")
    print("=" * 60 + "\n")
    
    schemas = [
        'ConversationCreate',
        'ConversationResponse',
        'MessageCreate',
        'AIMessageResponse',
        'AnalyzeRequest',
        'ModifyRequest',
        'PlanRequest',
        'MessageSchema',
    ]
    
    all_ok = True
    for schema_name in schemas:
        try:
            from app import schemas
            schema_cls = getattr(schemas, schema_name)
            print(f"  ✓ {schema_name:30} - 定义正确")
        except Exception as e:
            print(f"  ❌ {schema_name:30} - 定义错误: {e}")
            all_ok = False
    
    if all_ok:
        print("\n✅ 所有 Schemas 定义正确!")
    else:
        print("\n❌ 部分 Schemas 定义错误!")
    
    return all_ok


if __name__ == "__main__":
    print("\n🚀 开始验证 Conversations API...\n")
    
    # 验证 API 端点
    endpoints_ok = verify_api_endpoints()
    
    # 验证服务类
    services_ok = verify_services()
    
    # 验证 Schemas
    schemas_ok = verify_schemas()
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if endpoints_ok and services_ok and schemas_ok:
        print("\n✅ 所有验证通过! API 接口层已成功实现。")
        print("\n下一步:")
        print("  1. 运行后端服务: uvicorn app.main:app --reload")
        print("  2. 访问 API 文档: http://localhost:8000/docs")
        print("  3. 测试 API 端点")
        sys.exit(0)
    else:
        print("\n❌ 部分验证失败,请检查上述错误信息。")
        sys.exit(1)
