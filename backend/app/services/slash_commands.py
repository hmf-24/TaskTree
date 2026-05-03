"""
斜杠命令系统
============
参考 Claude Code 的斜杠命令优先解析机制，
为高频操作提供确定性入口，降低 LLM 理解成本。

设计原则 (来自 Claude Code handlePromptSubmit.ts:229):
- 斜杠命令优先于自然语言解析
- 支持别名 (如 /ls = /list)
- 参数以空格分隔
"""
import re
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum


class IntentType(str, Enum):
    """意图类型枚举 — 8 种核心意图"""
    QUERY_TASK_LIST = "query_task_list"
    QUERY_TASK_DETAIL = "query_task_detail"
    UPDATE_PROGRESS = "update_progress"
    CREATE_TASK = "create_task"
    MODIFY_TASK = "modify_task"
    ANALYZE_PROJECT = "analyze_project"
    PLAN_PROJECT = "plan_project"
    GENERAL_CHAT = "general_chat"


@dataclass
class IntentResult:
    """意图解析结果"""
    intent: IntentType
    confidence: float = 0.5
    params: Dict[str, Any] = field(default_factory=dict)
    task_reference: Optional[Dict[str, Any]] = None  # {"name": str, "id": int|None}
    clarification: Optional[str] = None
    raw_message: str = ""
    source: str = "unknown"  # slash_command / rule_engine / llm


@dataclass
class SlashCommand:
    """斜杠命令定义"""
    name: str
    aliases: List[str]
    description: str
    usage: str
    intent: IntentType
    parser: Optional[Callable] = None  # 自定义参数解析器


class SlashCommandRouter:
    """
    斜杠命令路由器
    
    参考 Claude Code 的斜杠命令解析:
    1. 检查是否以 '/' 开头
    2. 解析命令名和参数
    3. 查找命令（支持别名）
    4. 执行解析器或返回默认结果
    """
    
    def __init__(self):
        self.commands: Dict[str, SlashCommand] = {}
        self._register_commands()
    
    def _register_commands(self):
        """注册所有斜杠命令"""
        
        commands = [
            SlashCommand(
                name="list",
                aliases=["ls", "任务", "任务列表"],
                description="查看任务列表",
                usage="/list [项目名]",
                intent=IntentType.QUERY_TASK_LIST,
                parser=self._parse_list_args,
            ),
            SlashCommand(
                name="detail",
                aliases=["d", "详情", "查看"],
                description="查看任务详情",
                usage="/detail <任务名或#ID>",
                intent=IntentType.QUERY_TASK_DETAIL,
                parser=self._parse_detail_args,
            ),
            SlashCommand(
                name="done",
                aliases=["完成", "finish"],
                description="标记任务完成",
                usage="/done <任务名或#ID>",
                intent=IntentType.UPDATE_PROGRESS,
                parser=self._parse_done_args,
            ),
            SlashCommand(
                name="progress",
                aliases=["p", "进度"],
                description="更新任务进度",
                usage="/progress <任务名> <百分比>",
                intent=IntentType.UPDATE_PROGRESS,
                parser=self._parse_progress_args,
            ),
            SlashCommand(
                name="create",
                aliases=["new", "新建", "添加", "add"],
                description="创建新任务",
                usage="/create <任务名> [--priority high|medium|low]",
                intent=IntentType.CREATE_TASK,
                parser=self._parse_create_args,
            ),
            SlashCommand(
                name="modify",
                aliases=["mod", "改", "修改", "edit"],
                description="修改任务属性",
                usage="/modify <任务名或#ID> <属性> <新值>",
                intent=IntentType.MODIFY_TASK,
                parser=self._parse_modify_args,
            ),
            SlashCommand(
                name="analyze",
                aliases=["分析", "analysis"],
                description="分析项目状态",
                usage="/analyze [项目名]",
                intent=IntentType.ANALYZE_PROJECT,
                parser=self._parse_analyze_args,
            ),
            SlashCommand(
                name="plan",
                aliases=["规划", "planning"],
                description="项目规划建议",
                usage="/plan [项目名]",
                intent=IntentType.PLAN_PROJECT,
                parser=self._parse_plan_args,
            ),
            SlashCommand(
                name="help",
                aliases=["h", "帮助", "?"],
                description="查看帮助信息",
                usage="/help [命令名]",
                intent=IntentType.GENERAL_CHAT,
                parser=self._parse_help_args,
            ),
        ]
        
        for cmd in commands:
            # 注册主名称
            self.commands[cmd.name] = cmd
            # 注册别名
            for alias in cmd.aliases:
                self.commands[alias] = cmd
    
    def is_slash_command(self, message: str) -> bool:
        """检查消息是否是斜杠命令"""
        return message.strip().startswith("/")
    
    def parse(self, message: str) -> Optional[IntentResult]:
        """
        解析斜杠命令
        
        参考 Claude Code handlePromptSubmit.ts:229:
        ```
        const trimmedInput = finalInput.trim()
        const spaceIndex = trimmedInput.indexOf(' ')
        const commandName = spaceIndex === -1
            ? trimmedInput.slice(1)
            : trimmedInput.slice(1, spaceIndex)
        ```
        
        Args:
            message: 用户消息
            
        Returns:
            IntentResult 或 None (不是斜杠命令时)
        """
        trimmed = message.strip()
        
        if not trimmed.startswith("/"):
            return None
        
        # 解析命令名和参数
        space_index = trimmed.find(" ")
        if space_index == -1:
            command_name = trimmed[1:]
            command_args = ""
        else:
            command_name = trimmed[1:space_index]
            command_args = trimmed[space_index + 1:].strip()
        
        # 查找命令
        command = self.commands.get(command_name)
        if not command:
            return IntentResult(
                intent=IntentType.GENERAL_CHAT,
                confidence=0.9,
                params={"error": f"未知命令: /{command_name}"},
                raw_message=message,
                source="slash_command",
                clarification=self._format_unknown_command_help(command_name),
            )
        
        # 使用自定义解析器或默认处理
        if command.parser:
            result = command.parser(command_args)
        else:
            result = IntentResult(
                intent=command.intent,
                confidence=1.0,
                params={},
                raw_message=message,
                source="slash_command",
            )
        
        result.raw_message = message
        result.source = "slash_command"
        return result
    
    # ── 参数解析器 ────────────────────────────────────────────────

    def _parse_list_args(self, args: str) -> IntentResult:
        """解析 /list 参数"""
        params = {}
        if args:
            params["project_name"] = args.strip()
        
        return IntentResult(
            intent=IntentType.QUERY_TASK_LIST,
            confidence=1.0,
            params=params,
        )
    
    def _parse_detail_args(self, args: str) -> IntentResult:
        """解析 /detail 参数"""
        if not args:
            return IntentResult(
                intent=IntentType.QUERY_TASK_DETAIL,
                confidence=0.5,
                clarification="请指定任务名称或编号，如: /detail #123 或 /detail 用户登录",
            )
        
        task_ref = self._parse_task_reference(args)
        return IntentResult(
            intent=IntentType.QUERY_TASK_DETAIL,
            confidence=1.0,
            task_reference=task_ref,
        )
    
    def _parse_done_args(self, args: str) -> IntentResult:
        """解析 /done 参数"""
        if not args:
            return IntentResult(
                intent=IntentType.UPDATE_PROGRESS,
                confidence=0.5,
                clarification="请指定要完成的任务，如: /done 用户登录 或 /done #123",
            )
        
        task_ref = self._parse_task_reference(args)
        return IntentResult(
            intent=IntentType.UPDATE_PROGRESS,
            confidence=1.0,
            task_reference=task_ref,
            params={"status": "completed", "progress": 100},
        )
    
    def _parse_progress_args(self, args: str) -> IntentResult:
        """解析 /progress 参数"""
        if not args:
            return IntentResult(
                intent=IntentType.UPDATE_PROGRESS,
                confidence=0.5,
                clarification="请指定任务和进度，如: /progress 用户登录 80%",
            )
        
        # 提取百分比
        percent_match = re.search(r'(\d+)\s*%?$', args)
        progress = None
        task_part = args
        
        if percent_match:
            progress = int(percent_match.group(1))
            progress = min(100, max(0, progress))
            task_part = args[:percent_match.start()].strip()
        
        task_ref = self._parse_task_reference(task_part) if task_part else None
        
        params = {}
        if progress is not None:
            params["progress"] = progress
            if progress >= 100:
                params["status"] = "completed"
            elif progress > 0:
                params["status"] = "in_progress"
        
        return IntentResult(
            intent=IntentType.UPDATE_PROGRESS,
            confidence=1.0 if task_ref else 0.6,
            task_reference=task_ref,
            params=params,
            clarification="请指定任务名称" if not task_ref else None,
        )
    
    def _parse_create_args(self, args: str) -> IntentResult:
        """解析 /create 参数"""
        if not args:
            return IntentResult(
                intent=IntentType.CREATE_TASK,
                confidence=0.5,
                clarification="请输入要创建的任务名称，如: /create 实现搜索功能",
            )
        
        params = {"new_task_name": args}
        
        # 解析优先级标记
        priority_match = re.search(
            r'--priority\s+(high|medium|low)', args, re.IGNORECASE
        )
        if priority_match:
            params["priority"] = priority_match.group(1).lower()
            params["new_task_name"] = args[:priority_match.start()].strip()
        
        # 解析中文优先级
        for keyword, priority in [("高优先级", "high"), ("紧急", "high"),
                                  ("低优先级", "low"), ("不急", "low")]:
            if keyword in args:
                params["priority"] = priority
                params["new_task_name"] = args.replace(keyword, "").strip()
                break
        
        return IntentResult(
            intent=IntentType.CREATE_TASK,
            confidence=1.0,
            params=params,
        )
    
    def _parse_modify_args(self, args: str) -> IntentResult:
        """解析 /modify 参数"""
        if not args:
            return IntentResult(
                intent=IntentType.MODIFY_TASK,
                confidence=0.5,
                clarification="请指定要修改的任务和属性，如:\n"
                             "/modify #123 截止日期 2024-12-31\n"
                             "/modify 用户登录 优先级 高",
            )
        
        task_ref = self._parse_task_reference(args.split()[0] if args else "")
        
        params = {}
        remaining = " ".join(args.split()[1:]) if len(args.split()) > 1 else ""
        
        # 解析修改属性
        if remaining:
            if any(kw in remaining for kw in ["截止", "日期", "deadline"]):
                date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', remaining)
                if date_match:
                    params["due_date"] = date_match.group(1)
                
                days_match = re.search(r'(\d+)\s*天', remaining)
                if days_match:
                    params["extend_days"] = int(days_match.group(1))
            
            if any(kw in remaining for kw in ["优先级", "priority"]):
                if any(kw in remaining for kw in ["高", "high", "紧急"]):
                    params["priority"] = "high"
                elif any(kw in remaining for kw in ["低", "low"]):
                    params["priority"] = "low"
                else:
                    params["priority"] = "medium"
            
            if any(kw in remaining for kw in ["状态", "status"]):
                for kw, status in [("完成", "completed"), ("进行", "in_progress"),
                                   ("待办", "pending"), ("取消", "cancelled")]:
                    if kw in remaining:
                        params["status"] = status
                        break
        
        return IntentResult(
            intent=IntentType.MODIFY_TASK,
            confidence=0.9 if task_ref else 0.5,
            task_reference=task_ref,
            params=params,
        )
    
    def _parse_analyze_args(self, args: str) -> IntentResult:
        """解析 /analyze 参数"""
        params = {}
        if args:
            params["project_name"] = args.strip()
        
        return IntentResult(
            intent=IntentType.ANALYZE_PROJECT,
            confidence=1.0,
            params=params,
        )
    
    def _parse_plan_args(self, args: str) -> IntentResult:
        """解析 /plan 参数"""
        params = {}
        if args:
            params["project_name"] = args.strip()
        
        return IntentResult(
            intent=IntentType.PLAN_PROJECT,
            confidence=1.0,
            params=params,
        )
    
    def _parse_help_args(self, args: str) -> IntentResult:
        """解析 /help 参数"""
        if args:
            # 查找特定命令的帮助
            cmd = self.commands.get(args.strip())
            if cmd:
                help_text = (
                    f"## /{cmd.name}\n\n"
                    f"**说明**: {cmd.description}\n"
                    f"**用法**: `{cmd.usage}`\n"
                    f"**别名**: {', '.join('/' + a for a in cmd.aliases)}"
                )
            else:
                help_text = f"未知命令: /{args.strip()}\n\n" + self._format_help_text()
        else:
            help_text = self._format_help_text()
        
        return IntentResult(
            intent=IntentType.GENERAL_CHAT,
            confidence=1.0,
            params={"help_text": help_text},
        )
    
    # ── 工具方法 ──────────────────────────────────────────────────

    def _parse_task_reference(self, text: str) -> Optional[Dict[str, Any]]:
        """解析任务引用 (名称或 #ID)"""
        text = text.strip()
        if not text:
            return None
        
        # 匹配 #ID 格式
        id_match = re.match(r'^#(\d+)$', text)
        if id_match:
            return {"name": None, "id": int(id_match.group(1))}
        
        return {"name": text, "id": None}
    
    def _format_help_text(self) -> str:
        """生成帮助信息"""
        # 去重 (别名指向同一个命令)
        seen = set()
        unique_commands = []
        for cmd in self.commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                unique_commands.append(cmd)
        
        lines = ["## 📋 TaskTree 命令帮助\n"]
        for cmd in unique_commands:
            aliases_str = ", ".join(f"/{a}" for a in cmd.aliases[:2])
            lines.append(
                f"**/{cmd.name}** ({aliases_str})\n"
                f"  {cmd.description}\n"
                f"  用法: `{cmd.usage}`\n"
            )
        
        lines.append(
            "\n---\n"
            "💡 也可以直接用自然语言描述，如:\n"
            "「我的任务」「用户登录完成了」「创建一个搜索功能的任务」"
        )
        
        return "\n".join(lines)
    
    def _format_unknown_command_help(self, command_name: str) -> str:
        """生成未知命令的帮助提示"""
        return (
            f"未知命令: /{command_name}\n\n"
            f"输入 /help 查看所有可用命令\n"
            f"或直接用自然语言描述您的需求"
        )


# 全局单例
slash_command_router = SlashCommandRouter()
