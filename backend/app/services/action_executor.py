"""
动作执行器
==========
参考 Claude Code 的工具执行系统 (runToolUse)，
将意图解析结果路由到具体的任务操作。

设计原则 (来自 Claude Code):
- 查找工具 → 输入验证 → 权限检查 → 执行 → 结果处理
- 工具结果映射为 API 格式
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models import Task, Project
from app.services.slash_commands import IntentType, IntentResult
from app.services.task_matcher import TaskMatcherService
from app.services.task_updater import TaskUpdaterService
from app.services.message_printer import MessagePrinterService
from app.services.llm_service import LLMService
from app.services.intent_prompts import get_clarification_message
from app.schemas import ParseResultSchema


@dataclass
class ActionResult:
    """动作执行结果"""
    success: bool
    message: str  # 要发送给用户的消息
    msg_type: str = "markdown"  # text / markdown
    title: str = "TaskTree"
    data: Optional[Dict[str, Any]] = None


class ActionExecutor:
    """
    动作执行器
    
    根据 IntentResult 路由到具体操作:
    intent → handler → result → formatted message
    """
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
        self.task_matcher = TaskMatcherService(db)
        self.message_printer = MessagePrinterService()
        
        # 意图 → 处理器映射
        self._handlers = {
            IntentType.QUERY_TASK_LIST: self._handle_query_task_list,
            IntentType.QUERY_TASK_DETAIL: self._handle_query_task_detail,
            IntentType.UPDATE_PROGRESS: self._handle_update_progress,
            IntentType.CREATE_TASK: self._handle_create_task,
            IntentType.MODIFY_TASK: self._handle_modify_task,
            IntentType.ANALYZE_PROJECT: self._handle_analyze_project,
            IntentType.PLAN_PROJECT: self._handle_plan_project,
            IntentType.GENERAL_CHAT: self._handle_general_chat,
        }
    
    async def execute(
        self,
        intent: IntentResult,
        user_id: int
    ) -> ActionResult:
        """
        执行意图对应的动作
        
        Args:
            intent: 意图解析结果
            user_id: 用户 ID
            
        Returns:
            ActionResult: 执行结果
        """
        # 如果有澄清消息（低置信度），直接返回澄清
        if intent.clarification and intent.confidence < 0.4:
            return ActionResult(
                success=True,
                message=intent.clarification,
                msg_type="text",
            )
        
        # 查找处理器
        handler = self._handlers.get(intent.intent)
        if not handler:
            return ActionResult(
                success=False,
                message="暂不支持该操作",
                msg_type="text",
            )
        
        try:
            return await handler(intent, user_id)
        except Exception as e:
            print(f"❌ 执行动作失败: {e}")
            import traceback
            traceback.print_exc()
            return ActionResult(
                success=False,
                message=f"操作执行失败: {str(e)}",
                msg_type="text",
            )
    
    # ── 意图处理器 ────────────────────────────────────────────────

    async def _handle_query_task_list(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 查询任务列表"""
        query = select(Task).where(
            or_(Task.assignee_id == user_id),
            Task.status.in_(["pending", "in_progress"]),
        ).order_by(
            Task.due_date.asc().nulls_last(),
            Task.priority.desc(),
        ).limit(10)
        
        # 如果指定了项目名
        project_name = intent.params.get("project_name")
        if project_name:
            # 查找项目
            proj_result = await self.db.execute(
                select(Project).where(
                    Project.owner_id == user_id,
                    Project.name.ilike(f"%{project_name}%"),
                )
            )
            project = proj_result.scalar_one_or_none()
            if project:
                query = query.where(Task.project_id == project.id)
        
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        
        if not tasks:
            return ActionResult(
                success=True,
                message="🎉 您当前没有进行中或待处理的任务。",
                msg_type="text",
            )
        
        task_list_msg = self.message_printer.format_task_list(
            tasks, show_progress=True
        )
        return ActionResult(
            success=True,
            message=task_list_msg,
            msg_type="markdown",
            title="我的任务列表",
        )
    
    async def _handle_query_task_detail(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 查询任务详情"""
        # 解析任务引用
        task = await self._resolve_task(intent, user_id)
        
        if not task:
            if intent.clarification:
                return ActionResult(
                    success=True,
                    message=intent.clarification,
                    msg_type="text",
                )
            return ActionResult(
                success=False,
                message=get_clarification_message("missing_task_name"),
                msg_type="text",
            )
        
        # 格式化任务详情
        detail = f"""## 📋 任务详情

**任务名称**: {task.name}
**任务状态**: {task.status}
**完成进度**: {task.progress}%
**优先级**: {task.priority or '未设置'}
**截止时间**: {task.due_date.strftime('%Y-%m-%d') if task.due_date else '未设置'}
**描述**: {task.description or '无'}

---
*来自 TaskTree*"""
        
        return ActionResult(
            success=True,
            message=detail,
            msg_type="markdown",
            title=f"任务详情 - {task.name}",
        )
    
    async def _handle_update_progress(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 更新任务进度"""
        # 解析任务引用
        task = await self._resolve_task(intent, user_id)
        
        if not task:
            if intent.clarification:
                return ActionResult(
                    success=True,
                    message=intent.clarification,
                    msg_type="text",
                )
            return ActionResult(
                success=False,
                message=get_clarification_message("missing_task_name"),
                msg_type="text",
            )
        
        # 执行更新
        task_updater = TaskUpdaterService(self.db)
        old_status = task.status
        old_progress = task.progress
        
        parse_result = ParseResultSchema(
            type=intent.params.get("status", "in_progress"),
            progress=intent.params.get("progress", 0),
            description=intent.params.get("problem_description", ""),
            extend_days=intent.params.get("extend_days", 0),
            confidence=intent.confidence,
            keywords=[],
        )
        
        try:
            updated_task = await task_updater.update_from_feedback(
                task_id=task.id,
                parse_result=parse_result,
                user_id=user_id,
                message_content=intent.raw_message,
            )
            
            # 格式化确认消息
            confirmation_msg = self.message_printer.format_confirmation(
                task_name=updated_task.name,
                action=f"更新任务状态为 {updated_task.status}",
                old_value=f"{old_status} ({old_progress}%)",
                new_value=f"{updated_task.status} ({updated_task.progress}%)",
            )
            
            return ActionResult(
                success=True,
                message=confirmation_msg,
                msg_type="markdown",
                title=f"任务更新 - {updated_task.name}",
            )
            
        except PermissionError:
            return ActionResult(
                success=False,
                message=self.message_printer.format_error_message(
                    "permission_denied"
                ),
                msg_type="text",
            )
        except ValueError as e:
            return ActionResult(
                success=False,
                message=self.message_printer.format_error_message(
                    "parse_failed", str(e)
                ),
                msg_type="text",
            )
    
    async def _handle_create_task(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 创建新任务"""
        task_name = intent.params.get("new_task_name", "").strip()
        
        if not task_name:
            return ActionResult(
                success=True,
                message="请指定任务名称，如: /create 实现搜索功能",
                msg_type="text",
            )
        
        # 获取用户的第一个活跃项目
        proj_result = await self.db.execute(
            select(Project).where(
                Project.owner_id == user_id,
                Project.status == "active",
            ).order_by(Project.updated_at.desc()).limit(1)
        )
        project = proj_result.scalar_one_or_none()
        
        if not project:
            return ActionResult(
                success=False,
                message="您还没有活跃的项目，请先在 TaskTree 中创建项目。",
                msg_type="text",
            )
        
        # 创建任务
        from datetime import datetime, timezone
        
        new_task = Task(
            name=task_name,
            project_id=project.id,
            assignee_id=user_id,
            status="pending",
            priority=intent.params.get("priority", "medium"),
            progress=0,
            description=intent.params.get("description", ""),
        )
        
        self.db.add(new_task)
        await self.db.commit()
        await self.db.refresh(new_task)
        
        priority_emoji = {
            "high": "🔴 高",
            "medium": "🟡 中",
            "low": "🟢 低",
        }
        
        msg = f"""## ✅ 任务创建成功

**任务名称**: {new_task.name}
**所属项目**: {project.name}
**优先级**: {priority_emoji.get(new_task.priority, new_task.priority)}
**状态**: 待办

---
*来自 TaskTree*"""
        
        return ActionResult(
            success=True,
            message=msg,
            msg_type="markdown",
            title=f"新任务 - {new_task.name}",
        )
    
    async def _handle_modify_task(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 修改任务属性"""
        # 解析任务引用
        task = await self._resolve_task(intent, user_id)
        
        if not task:
            if intent.clarification:
                return ActionResult(
                    success=True,
                    message=intent.clarification,
                    msg_type="text",
                )
            return ActionResult(
                success=False,
                message=get_clarification_message("missing_task_name"),
                msg_type="text",
            )
        
        # 使用 TaskModifier 执行修改
        from app.services.task_modifier import TaskModifier
        modifier = TaskModifier(self.db, self.llm_service)
        
        # 如果参数中有明确的修改项，直接执行
        params = intent.params
        modifications = {}
        
        if "priority" in params:
            modifications["priority"] = params["priority"]
        if "status" in params:
            modifications["status"] = params["status"]
        if "due_date" in params:
            modifications["due_date"] = params["due_date"]
        if "extend_days" in params:
            modifications["extend_days"] = params["extend_days"]
        if "description" in params:
            modifications["description"] = params["description"]
        
        if not modifications:
            # 没有明确的修改项，让 LLM 解析
            try:
                intent_result = await modifier.parse_modification_intent(
                    intent.raw_message, [task]
                )
                
                if intent_result.get("confidence", 0) < 0.5:
                    return ActionResult(
                        success=True,
                        message=(
                            f"我找到了任务 **{task.name}**，但不确定您想修改什么。\n"
                            f"请更具体地描述，比如:\n"
                            f"- 修改截止日期: 「/modify {task.name} 截止日期 2025-01-01」\n"
                            f"- 修改优先级: 「/modify {task.name} 优先级 高」\n"
                            f"- 修改状态: 「/modify {task.name} 状态 完成」"
                        ),
                        msg_type="markdown",
                    )
                
                # 执行 LLM 解析的修改
                modification_result = await modifier.execute_modification(
                    intent_result
                )
                
                return ActionResult(
                    success=modification_result["success_count"] > 0,
                    message=intent_result.get(
                        "confirmation_message",
                        f"已成功修改任务 {task.name}"
                    ),
                    msg_type="markdown",
                    title=f"任务修改 - {task.name}",
                )
                
            except Exception as e:
                return ActionResult(
                    success=False,
                    message=f"修改任务失败: {str(e)}",
                    msg_type="text",
                )
        
        # 直接执行修改
        modification = {
            "action": "batch_update",
            "task_ids": [task.id],
            "params": modifications,
        }
        
        result = await modifier.execute_modification(modification)
        
        changes = []
        if "priority" in modifications:
            changes.append(f"优先级 → {modifications['priority']}")
        if "status" in modifications:
            changes.append(f"状态 → {modifications['status']}")
        if "due_date" in modifications:
            changes.append(f"截止日期 → {modifications['due_date']}")
        if "extend_days" in modifications:
            changes.append(f"截止日期延后 {modifications['extend_days']} 天")
        
        msg = f"""## ✏️ 任务修改成功

**任务**: {task.name}
**修改内容**:
{chr(10).join('- ' + c for c in changes)}

---
*来自 TaskTree*"""
        
        return ActionResult(
            success=True,
            message=msg,
            msg_type="markdown",
            title=f"任务修改 - {task.name}",
        )
    
    async def _handle_analyze_project(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 分析项目"""
        from app.services.task_analyzer import TaskAnalyzer
        
        # 获取用户的项目
        project_name = intent.params.get("project_name")
        if project_name:
            proj_result = await self.db.execute(
                select(Project).where(
                    Project.owner_id == user_id,
                    Project.name.ilike(f"%{project_name}%"),
                )
            )
        else:
            proj_result = await self.db.execute(
                select(Project).where(
                    Project.owner_id == user_id,
                    Project.status == "active",
                ).order_by(Project.updated_at.desc()).limit(1)
            )
        
        project = proj_result.scalar_one_or_none()
        
        if not project:
            return ActionResult(
                success=False,
                message="未找到匹配的项目",
                msg_type="text",
            )
        
        analyzer = TaskAnalyzer(self.db, self.llm_service)
        analysis = await analyzer.analyze_project_tasks(
            project.id, user_id
        )
        
        # 格式化分析结果
        msg = f"""## 📊 项目分析 - {project.name}

**概要**: {analysis.get('summary', '暂无')}
**风险评分**: {analysis.get('risk_score', 0)}/100

"""
        
        issues = analysis.get("issues", [])
        if issues:
            msg += "### ⚠️ 发现的问题\n\n"
            for issue in issues[:5]:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                msg += (
                    f"{severity_emoji.get(issue.get('severity', 'low'), '⚪')} "
                    f"**{issue.get('description', '')}**\n"
                    f"  建议: {issue.get('suggestion', '')}\n\n"
                )
        
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            msg += "### 💡 优化建议\n\n"
            for rec in recommendations[:5]:
                msg += f"- {rec.get('details', '')}\n"
        
        msg += "\n---\n*来自 TaskTree*"
        
        return ActionResult(
            success=True,
            message=msg,
            msg_type="markdown",
            title=f"项目分析 - {project.name}",
        )
    
    async def _handle_plan_project(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 规划项目"""
        from app.services.project_planner import ProjectPlanner
        
        # 获取用户的项目
        proj_result = await self.db.execute(
            select(Project).where(
                Project.owner_id == user_id,
                Project.status == "active",
            ).order_by(Project.updated_at.desc()).limit(1)
        )
        project = proj_result.scalar_one_or_none()
        
        if not project:
            return ActionResult(
                success=False,
                message="未找到活跃项目",
                msg_type="text",
            )
        
        planner = ProjectPlanner(self.db, self.llm_service)
        plan = await planner.analyze_and_plan(
            project.id, user_id,
            planning_goal=intent.params.get("goal")
        )
        
        msg = f"""## 📋 项目规划 - {project.name}

**概要**: {plan.get('summary', '暂无')}

"""
        
        missing_tasks = plan.get("missing_tasks", [])
        if missing_tasks:
            msg += "### 📝 建议新增任务\n\n"
            for task in missing_tasks[:5]:
                msg += (
                    f"- **{task.get('name', '')}**: "
                    f"{task.get('reason', '')}\n"
                )
        
        improvements = plan.get("structure_improvements", [])
        if improvements:
            msg += "\n### 🔧 改进建议\n\n"
            for imp in improvements[:3]:
                msg += f"- {imp.get('suggestion', '')}\n"
        
        msg += "\n---\n*来自 TaskTree*"
        
        return ActionResult(
            success=True,
            message=msg,
            msg_type="markdown",
            title=f"项目规划 - {project.name}",
        )
    
    async def _handle_general_chat(
        self, intent: IntentResult, user_id: int
    ) -> ActionResult:
        """处理: 闲聊/帮助/其他"""
        # 如果有帮助文本，直接返回
        help_text = intent.params.get("help_text")
        if help_text:
            return ActionResult(
                success=True,
                message=help_text,
                msg_type="markdown",
                title="帮助",
            )
        
        # 如果 LLM 生成了直接的回答
        reply = intent.params.get("reply")
        if reply:
            return ActionResult(
                success=True,
                message=reply,
                msg_type="text",
            )
        
        # 如果有错误信息
        error = intent.params.get("error")
        if error:
            return ActionResult(
                success=True,
                message=error,
                msg_type="text",
            )
        
        # 如果有澄清消息
        if intent.clarification:
            return ActionResult(
                success=True,
                message=intent.clarification,
                msg_type="text",
            )
        
        # 默认: 友好的引导消息
        return ActionResult(
            success=True,
            message=(
                "👋 你好！我是 TaskTree 助手，可以帮你管理任务。\n\n"
                "你可以试试:\n"
                "- 「我的任务」查看任务列表\n"
                "- 「XX完成了」更新任务进度\n"
                "- 「创建任务：XX」创建新任务\n"
                "- 输入 /help 查看所有命令"
            ),
            msg_type="text",
        )
    
    # ── 工具方法 ──────────────────────────────────────────────────

    async def _resolve_task(
        self, intent: IntentResult, user_id: int
    ) -> Optional[Task]:
        """
        根据意图中的任务引用解析具体任务
        
        优先使用 task_reference，然后使用 keywords 进行匹配
        """
        task_ref = intent.task_reference
        
        if not task_ref:
            return None
        
        # 如果有 ID，直接查询
        if task_ref.get("id"):
            result = await self.db.execute(
                select(Task).where(Task.id == task_ref["id"])
            )
            task = result.scalar_one_or_none()
            if task:
                return task
        
        # 如果有名称，使用 TaskMatcher
        if task_ref.get("name"):
            keywords = [task_ref["name"]]
            matched = await self.task_matcher.match(
                keywords=keywords,
                user_id=user_id,
                limit=1,
            )
            
            if matched:
                return matched[0]
            
            # 尝试用名称的子串匹配
            words = task_ref["name"].split()
            if len(words) > 1:
                matched = await self.task_matcher.match(
                    keywords=words,
                    user_id=user_id,
                    limit=1,
                )
                if matched:
                    return matched[0]
        
        return None
