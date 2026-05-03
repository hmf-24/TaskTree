"""
意图解析系统单元测试
====================
测试 SlashCommandRouter, IntentResolver 的规则引擎层,
以及 IntentPrompts 的模板构建。
"""
import pytest
from app.services.slash_commands import (
    SlashCommandRouter,
    IntentType,
    IntentResult,
)
from app.services.intent_prompts import (
    build_intent_system_prompt,
    build_intent_user_prompt,
    get_clarification_message,
)


# ── SlashCommandRouter 测试 ─────────────────────────────────────

class TestSlashCommandRouter:
    """斜杠命令路由器测试"""
    
    def setup_method(self):
        self.router = SlashCommandRouter()
    
    # -- 基础功能 --
    
    def test_is_slash_command(self):
        assert self.router.is_slash_command("/list")
        assert self.router.is_slash_command("/help")
        assert not self.router.is_slash_command("list")
        assert not self.router.is_slash_command("我的任务")
    
    def test_parse_not_slash_command(self):
        result = self.router.parse("我的任务")
        assert result is None
    
    # -- /list --
    
    def test_list_command(self):
        result = self.router.parse("/list")
        assert result.intent == IntentType.QUERY_TASK_LIST
        assert result.confidence == 1.0
        assert result.source == "slash_command"
    
    def test_list_alias_ls(self):
        result = self.router.parse("/ls")
        assert result.intent == IntentType.QUERY_TASK_LIST
    
    def test_list_alias_chinese(self):
        result = self.router.parse("/任务")
        assert result.intent == IntentType.QUERY_TASK_LIST
    
    def test_list_with_project(self):
        result = self.router.parse("/list 我的项目")
        assert result.intent == IntentType.QUERY_TASK_LIST
        assert result.params.get("project_name") == "我的项目"
    
    # -- /done --
    
    def test_done_command(self):
        result = self.router.parse("/done 用户登录")
        assert result.intent == IntentType.UPDATE_PROGRESS
        assert result.confidence == 1.0
        assert result.task_reference == {"name": "用户登录", "id": None}
        assert result.params.get("status") == "completed"
        assert result.params.get("progress") == 100
    
    def test_done_with_id(self):
        result = self.router.parse("/done #123")
        assert result.task_reference == {"name": None, "id": 123}
    
    def test_done_no_args(self):
        result = self.router.parse("/done")
        assert result.confidence == 0.5
        assert result.clarification is not None
    
    # -- /progress --
    
    def test_progress_command(self):
        result = self.router.parse("/progress 用户登录 80%")
        assert result.intent == IntentType.UPDATE_PROGRESS
        assert result.params.get("progress") == 80
        assert result.params.get("status") == "in_progress"
        assert result.task_reference == {"name": "用户登录", "id": None}
    
    def test_progress_100_percent(self):
        result = self.router.parse("/progress 搜索功能 100%")
        assert result.params.get("progress") == 100
        assert result.params.get("status") == "completed"
    
    # -- /create --
    
    def test_create_command(self):
        result = self.router.parse("/create 实现搜索功能")
        assert result.intent == IntentType.CREATE_TASK
        assert result.params.get("new_task_name") == "实现搜索功能"
        assert result.confidence == 1.0
    
    def test_create_with_priority(self):
        result = self.router.parse("/create 修复Bug --priority high")
        assert result.params.get("new_task_name") == "修复Bug"
        assert result.params.get("priority") == "high"
    
    def test_create_with_chinese_priority(self):
        result = self.router.parse("/create 紧急修复登录问题")
        assert result.params.get("priority") == "high"
    
    def test_create_no_args(self):
        result = self.router.parse("/create")
        assert result.confidence == 0.5
        assert result.clarification is not None
    
    # -- /modify --
    
    def test_modify_priority(self):
        result = self.router.parse("/modify #123 优先级 高")
        assert result.intent == IntentType.MODIFY_TASK
        assert result.task_reference == {"name": None, "id": 123}
        assert result.params.get("priority") == "high"
    
    # -- /analyze --
    
    def test_analyze_command(self):
        result = self.router.parse("/analyze")
        assert result.intent == IntentType.ANALYZE_PROJECT
        assert result.confidence == 1.0
    
    def test_analyze_alias_chinese(self):
        result = self.router.parse("/分析")
        assert result.intent == IntentType.ANALYZE_PROJECT
    
    # -- /help --
    
    def test_help_command(self):
        result = self.router.parse("/help")
        assert result.intent == IntentType.GENERAL_CHAT
        assert "help_text" in result.params
        assert "TaskTree" in result.params["help_text"]
    
    def test_help_specific_command(self):
        result = self.router.parse("/help list")
        assert "查看任务列表" in result.params["help_text"]
    
    # -- 未知命令 --
    
    def test_unknown_command(self):
        result = self.router.parse("/unknown")
        assert result.intent == IntentType.GENERAL_CHAT
        assert result.clarification is not None
        assert "未知命令" in result.clarification


# ── IntentResolver 规则引擎测试 ─────────────────────────────────

class TestRuleEngine:
    """IntentResolver 规则引擎测试 (不需要 db/llm)"""
    
    def setup_method(self):
        from app.services.intent_resolver import IntentResolver
        # 创建一个不需要 db 和 llm 的实例来测试规则引擎
        self.resolver = IntentResolver.__new__(IntentResolver)
        self.resolver.slash_router = SlashCommandRouter()
    
    # -- 查询任务列表 --
    
    def test_rule_query_task_list(self):
        result = self.resolver._try_rule_engine("我的任务")
        assert result.intent == IntentType.QUERY_TASK_LIST
        assert result.confidence >= 0.85
    
    def test_rule_query_task_list_variants(self):
        for msg in ["任务列表", "我有哪些任务", "所有任务", "查任务"]:
            result = self.resolver._try_rule_engine(msg)
            assert result.intent == IntentType.QUERY_TASK_LIST, f"Failed for: {msg}"
    
    def test_rule_query_task_list_exact(self):
        for msg in ["list", "ls", "任务"]:
            result = self.resolver._try_rule_engine(msg)
            assert result.intent == IntentType.QUERY_TASK_LIST, f"Failed for: {msg}"
    
    # -- 完成任务 --
    
    def test_rule_completed_task(self):
        result = self.resolver._try_rule_engine("用户登录完成了")
        assert result.intent == IntentType.UPDATE_PROGRESS
        assert result.confidence >= 0.85
        assert result.task_reference is not None
        assert result.task_reference["name"] is not None
        assert len(result.task_reference["name"]) > 0
        assert result.params.get("status") == "completed"
    
    def test_rule_completed_variants(self):
        variants = ["用户登录做完了", "用户登录搞定了"]
        for msg in variants:
            result = self.resolver._try_rule_engine(msg)
            assert result.intent == IntentType.UPDATE_PROGRESS, f"Failed for: {msg}"
            assert result.params.get("status") == "completed"
    
    # -- 进度更新 --
    
    def test_rule_progress_update(self):
        result = self.resolver._try_rule_engine("用户登录 进度 80%")
        assert result.intent == IntentType.UPDATE_PROGRESS
        assert result.params.get("progress") == 80
        assert result.task_reference["name"] == "用户登录"
    
    # -- 创建任务 --
    
    def test_rule_create_task(self):
        result = self.resolver._try_rule_engine("创建任务：实现搜索功能")
        assert result.intent == IntentType.CREATE_TASK
        assert result.confidence >= 0.85
        assert "实现搜索功能" in result.params.get("new_task_name", "")
    
    def test_rule_create_with_help(self):
        result = self.resolver._try_rule_engine("帮我创建一个优化数据库的任务")
        assert result.intent == IntentType.CREATE_TASK
    
    # -- 分析项目 --
    
    def test_rule_analyze(self):
        result = self.resolver._try_rule_engine("分析一下项目进展")
        assert result.intent == IntentType.ANALYZE_PROJECT
        assert result.confidence >= 0.85
    
    # -- 帮助 --
    
    def test_rule_help(self):
        result = self.resolver._try_rule_engine("帮助")
        assert result.intent == IntentType.GENERAL_CHAT
        assert "help_text" in result.params
    
    # -- 模糊意图 (低置信度) --
    
    def test_rule_ambiguous_query(self):
        result = self.resolver._try_rule_engine("看看这个任务怎么样")
        assert result is not None
        assert result.confidence < 0.85  # 低置信度，会交给 LLM
    
    def test_rule_totally_ambiguous(self):
        result = self.resolver._try_rule_engine("好的谢谢")
        assert result is None  # 完全无法猜测


# ── IntentPrompts 测试 ──────────────────────────────────────────

class TestIntentPrompts:
    """System Prompt 模板构建测试"""
    
    def test_build_system_prompt_empty_context(self):
        prompt = build_intent_system_prompt({})
        assert "TaskTree" in prompt
        assert "query_task_list" in prompt
        assert "JSON" in prompt
    
    def test_build_system_prompt_with_context(self):
        context = {
            "user_id": 1,
            "username": "张三",
            "projects": [{"name": "测试项目", "task_count": 5, "completed_count": 2}],
            "tasks": [
                {
                    "id": 1,
                    "name": "用户登录",
                    "status": "in_progress",
                    "priority": "high",
                    "progress": 60,
                }
            ],
            "recent_messages": [],
        }
        prompt = build_intent_system_prompt(context)
        assert "张三" in prompt
        assert "测试项目" in prompt
        assert "用户登录" in prompt
    
    def test_build_user_prompt(self):
        prompt = build_intent_user_prompt("我的任务")
        assert "我的任务" in prompt
    
    def test_clarification_message(self):
        msg = get_clarification_message("ambiguous_intent")
        assert "查看任务列表" in msg
        
        msg2 = get_clarification_message("missing_task_name")
        assert "任务名称" in msg2
