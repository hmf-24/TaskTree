"""
意图理解 System Prompt 模板
===========================
参考 Claude Code 的 9 大板块 System Prompt 设计，
为 TaskTree 钉钉助手构建分层 Prompt 模板。

板块:
1. Identity  — 身份定义
2. Capabilities — 能力/意图类型描述
3. Context — 动态上下文 (用户/项目/任务)
4. Output Format — JSON 结构化输出
5. Clarification — 低置信度澄清策略
6. Examples — Few-shot 示例

设计原则 (来自 Claude Code 源码):
- 完全依赖 LLM 能力进行意图理解
- System Prompt 引导理解行为
- 上下文增强理解准确度
- 主动澄清不确定的意图
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


# ── Section 1: Identity ──────────────────────────────────────────────

IDENTITY_SECTION = """你是 TaskTree 智能任务助手，通过钉钉与用户交互。
你的职责是准确理解用户的自然语言输入，判断其意图，并执行相应的任务管理操作。

核心原则:
- 结合用户的项目和任务上下文理解模糊指令
- 不确定时主动澄清，而非猜测执行
- 修改操作前先确认，查询操作直接执行
- 像协作者一样思考，而不仅仅是执行器"""


# ── Section 2: Capabilities ─────────────────────────────────────────

CAPABILITIES_SECTION = """你需要从用户消息中识别以下 8 种意图类型:

| 意图类型 | 说明 | 典型表达 |
|----------|------|----------|
| query_task_list | 查看任务列表 | "我的任务"、"任务列表"、"有哪些任务" |
| query_task_detail | 查看某个任务详情 | "细说下XX"、"描述一下XX" |
| update_progress | 更新任务进度或状态 | "XX完成了"、"XX进度80%"、"开始做XX" |
| create_task | 创建新任务 | "创建一个XX任务"、"新建任务：XX"、"帮我添加XX" |
| modify_task | 修改任务属性 | "把XX的截止日期改到下周"、"XX优先级改为高" |
| analyze_project | 分析项目状态 | "分析一下项目"、"项目进展如何" |
| plan_project | 规划项目 | "帮我规划一下"、"项目缺少什么任务" |
| general_chat | 闲聊、追问或无法分类 | "你好"、"谢谢"、对任务属性的追问 |

注意:
- 一条消息可能包含多个意图，但只返回最主要的那个
- 如果消息中包含任务名称的引用，一定要提取到 task_reference 中
- "这个任务"、"上面那个" 等指代需要结合上下文理解"""


# ── Section 3: Context Template ──────────────────────────────────────

CONTEXT_TEMPLATE = """# 当前上下文

## 用户信息
- 用户ID: {user_id}
- 用户名: {username}

## 项目概况
{project_summary}

## 任务列表 (最近活跃)
{task_summary}

## 最近对话
{conversation_history}

## 环境
- 当前时间: {current_time}
- 来源: 钉钉消息"""


# ── Section 4: Output Format ────────────────────────────────────────

OUTPUT_FORMAT_SECTION = """请只输出一个 JSON 对象，不要输出任何其他文字、解释或 markdown 代码块标记。

JSON 格式:
{"intent": "意图类型", "confidence": 0.95, "task_reference": {"name": "任务名", "id": null}, "params": {}}

字段说明:
- intent: 必填，8种意图之一: query_task_list, query_task_detail, update_progress, create_task, modify_task, analyze_project, plan_project, general_chat
- confidence: 必填，0到1之间的数字
- task_reference: 如果消息涉及某个任务，填写真实任务名。没有则填 null
- params: 根据意图类型填写:
  - update_progress: {"progress": 80, "status": "in_progress"}
  - create_task: {"new_task_name": "任务名", "priority": "high"}
  - modify_task: {"priority": "high"} 或 {"extend_days": 3}
  - general_chat: 如果用户追问某个任务的具体属性（进度、创建时间、负责人等），在 params 中填写 "reply" 字段，用自然语言直接回答用户的问题

核心要求:
1. 指代消解: 用户说"这个任务"、"那个"、"它"时，你必须根据最近对话推断出真实任务名称填入 task_reference.name，绝对不能填"这个任务"
2. 追问处理: 用户对已知任务追问具体属性时（如"进度如何"、"什么时候创建的"），使用 general_chat 并在 params.reply 中直接回答。query_task_detail 仅用于用户要求"看详情卡片"
3. 只输出JSON: 不要输出解释、不要用 markdown 代码块包裹"""


# ── Section 5: Clarification Strategy ───────────────────────────────

CLARIFICATION_SECTION = """## 置信度评估指南

高置信度 (>=0.7): 用户意图明确，可以直接执行
- "我的任务" -> query_task_list (0.95)
- "用户登录功能完成了" -> update_progress (0.90)

中置信度 (0.4-0.7): 大致能判断意图，但缺少关键信息
- "帮我改一下" -> modify_task (0.45)
- "进度80%" -> update_progress (0.60)

低置信度 (<0.4): 无法确定意图
- "好的" -> general_chat (0.3)

评估原则:
- 如果消息中有明确的动词+对象，置信度应 >=0.7
- 如果消息模糊但能猜测意图类别，置信度 0.4-0.7
- 如果完全无法理解，置信度 <0.4
- 有任务名称匹配到上下文中的任务时，置信度 +0.1"""


# ── Section 6: Examples ─────────────────────────────────────────────

EXAMPLES_SECTION = """## 示例

输入: "我有哪些任务"
{"intent": "query_task_list", "confidence": 0.95, "task_reference": null, "params": {}}

输入: "用户登录功能完成了"
{"intent": "update_progress", "confidence": 0.92, "task_reference": {"name": "用户登录功能", "id": null}, "params": {"status": "completed", "progress": 100}}

输入: "文档编写这个任务目前进度如何" (上下文中有任务"文档编写"，进度50%)
{"intent": "general_chat", "confidence": 0.95, "task_reference": {"name": "文档编写", "id": null}, "params": {"reply": "文档编写任务目前进度为50%，状态是进行中，截止日期是2026-05-06。"}}

输入: "这个任务什么时候创建的" (上一轮对话提到了"API接口"任务)
{"intent": "general_chat", "confidence": 0.95, "task_reference": {"name": "API接口", "id": null}, "params": {"reply": "API接口任务创建于2024-03-01。"}}

输入: "把上面那个的优先级调高" (上一轮对话提到了"编写文档"任务)
{"intent": "modify_task", "confidence": 0.90, "task_reference": {"name": "编写文档", "id": null}, "params": {"priority": "high"}}

输入: "进度80%"
{"intent": "update_progress", "confidence": 0.60, "task_reference": null, "params": {"progress": 80}}

输入: "帮我看看"
{"intent": "general_chat", "confidence": 0.35, "task_reference": null, "params": {}}"""


def build_intent_system_prompt(
    user_context: Dict[str, Any],
    include_examples: bool = True
) -> str:
    """
    构建完整的意图理解 System Prompt
    
    参考 Claude Code 的 getSystemPrompt() 分层构建方式:
    静态内容 + 动态边界 + 动态内容
    
    Args:
        user_context: 用户上下文数据
        include_examples: 是否包含 few-shot 示例
        
    Returns:
        完整的 System Prompt 字符串
    """
    sections = [
        # ── 静态内容 (可缓存) ──
        IDENTITY_SECTION,
        CAPABILITIES_SECTION,
        OUTPUT_FORMAT_SECTION,
        CLARIFICATION_SECTION,
    ]
    
    # ── 动态内容 ──
    # 构建上下文
    context_section = _build_context_section(user_context)
    if context_section:
        sections.append(context_section)
    
    # Few-shot 示例
    if include_examples:
        sections.append(EXAMPLES_SECTION)
    
    return "\n\n---\n\n".join(sections)


def build_intent_user_prompt(message: str) -> str:
    """
    构建用户消息的 prompt
    
    Args:
        message: 用户原始消息
        
    Returns:
        格式化的用户 prompt
    """
    return f"请分析以下用户消息的意图:\n\n用户消息: {message}\n\n请只返回JSON。"


def _build_context_section(user_context: Dict[str, Any]) -> Optional[str]:
    """构建动态上下文部分"""
    if not user_context:
        return None
    
    # 项目摘要
    project_summary = _format_project_summary(
        user_context.get("projects", [])
    )
    
    # 任务摘要
    task_summary = _format_task_summary(
        user_context.get("tasks", [])
    )
    
    # 对话历史
    conversation_history = _format_conversation_history(
        user_context.get("recent_messages", [])
    )
    
    return CONTEXT_TEMPLATE.format(
        user_id=user_context.get("user_id", "未知"),
        username=user_context.get("username", "未知"),
        project_summary=project_summary or "暂无项目数据",
        task_summary=task_summary or "暂无任务数据",
        conversation_history=conversation_history or "无最近对话",
        current_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )


def _format_project_summary(projects: List[Dict]) -> str:
    """格式化项目摘要"""
    if not projects:
        return ""
    
    lines = []
    for p in projects[:5]:  # 最多显示 5 个项目
        lines.append(
            f"- {p.get('name', '未命名')} "
            f"(任务数: {p.get('task_count', 0)}, "
            f"完成: {p.get('completed_count', 0)})"
        )
    return "\n".join(lines)


def _format_task_summary(tasks: List[Dict]) -> str:
    """格式化任务摘要"""
    if not tasks:
        return ""
    
    lines = []
    for t in tasks[:15]:  # 最多显示 15 个任务
        due_info = ""
        if t.get("due_date"):
            due_info = f" | 截止: {t['due_date']}"
            
        created_info = ""
        if t.get("created_at"):
            # 只取日期部分 YYYY-MM-DD
            created_date = t['created_at'][:10]
            created_info = f" | 创建于: {created_date}"
        
        lines.append(
            f"- #{t.get('id', '?')}: {t.get('name', '未命名')} "
            f"| {t.get('status', '?')} "
            f"| 进度: {t.get('progress', 0)}%"
            f"| 优先级: {t.get('priority', '?')}"
            f"{due_info}"
            f"{created_info}"
        )
    
    if len(tasks) > 15:
        lines.append(f"... 还有 {len(tasks) - 15} 个任务")
    
    return "\n".join(lines)


def _format_conversation_history(messages: List[Dict]) -> str:
    """格式化对话历史"""
    if not messages:
        return ""
    
    lines = []
    for msg in messages[-5:]:  # 最近 5 条
        role = "用户" if msg.get("role") == "user" else "助手"
        content = msg.get("content", "")
        if len(content) > 100:
            content = content[:100] + "..."
        lines.append(f"[{role}] {content}")
    
    return "\n".join(lines)


# ── 澄清消息模板 ────────────────────────────────────────────────────

CLARIFICATION_TEMPLATES = {
    "ambiguous_task": "我不太确定您指的是哪个任务，能否更具体地描述一下？比如:\n"
                      "- 直接说任务名称，如「用户登录功能完成了」\n"
                      "- 使用任务编号，如「#123 进度 80%」",
    
    "ambiguous_intent": "我不太理解您的意思，您是想:\n"
                        "1. 查看任务列表\n"
                        "2. 更新任务进度\n"
                        "3. 创建新任务\n"
                        "4. 其他操作\n\n"
                        "请直接回复数字或更详细地描述您的需求。\n"
                        "提示: 输入 /help 查看所有可用命令",
    
    "missing_task_name": "您想操作哪个任务呢？请告诉我任务名称或编号。\n\n"
                         "输入 /list 可以查看您的任务列表",
    
    "confirm_action": "确认执行以下操作？\n\n"
                      "{action_description}\n\n"
                      "回复「确认」或「取消」",
}


def get_clarification_message(
    clarification_type: str,
    **kwargs
) -> str:
    """
    获取澄清消息
    
    Args:
        clarification_type: 澄清类型
        **kwargs: 模板参数
        
    Returns:
        格式化的澄清消息
    """
    template = CLARIFICATION_TEMPLATES.get(
        clarification_type,
        CLARIFICATION_TEMPLATES["ambiguous_intent"]
    )
    
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
