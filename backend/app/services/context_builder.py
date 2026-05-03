"""
上下文构建器
============
参考 Claude Code 的 computeSimpleEnvInfo() 和动态 System Prompt 分段机制，
为意图理解注入用户、项目、任务、对话历史等上下文信息。

设计原则 (来自 Claude Code):
- 工作目录上下文增强理解 → 我们注入项目/任务上下文
- 动态内容每轮重新计算 → 我们每次消息构建最新上下文
- 上下文压缩控制 token 用量 → 我们限制任务数量和消息长度
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from datetime import datetime, timezone

from app.models import User, Project, Task, AIConversation


class ContextBuilder:
    """
    上下文构建器
    
    为 IntentResolver 提供结构化的用户上下文，
    注入到 LLM 的 System Prompt 中增强意图理解。
    """
    
    # 控制上下文规模，避免 token 浪费
    MAX_PROJECTS = 5
    MAX_TASKS = 15
    MAX_RECENT_MESSAGES = 5
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def build(
        self,
        user_id: int,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        构建完整的用户上下文
        
        Args:
            user_id: 用户 ID
            project_id: 可选的项目 ID (限定上下文范围)
            
        Returns:
            结构化的上下文数据
        """
        context = {
            "user_id": user_id,
            "username": "",
            "projects": [],
            "tasks": [],
            "recent_messages": [],
            "stats": {},
        }
        
        # 1. 加载用户信息
        user_info = await self._load_user_info(user_id)
        context.update(user_info)
        
        # 2. 加载项目列表
        context["projects"] = await self._load_projects(user_id, project_id)
        
        # 3. 加载活跃任务
        context["tasks"] = await self._load_active_tasks(
            user_id, project_id
        )
        
        # 4. 加载最近的钉钉对话历史
        context["recent_messages"] = await self._load_recent_messages(
            user_id
        )
        
        # 5. 计算统计信息
        context["stats"] = self._compute_stats(context["tasks"])
        
        return context
    
    async def _load_user_info(self, user_id: int) -> Dict[str, Any]:
        """加载用户基本信息"""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    "username": user.nickname or user.email or f"用户{user_id}",
                }
        except Exception as e:
            print(f"⚠️ 加载用户信息失败: {e}")
        
        return {"username": f"用户{user_id}"}
    
    async def _load_projects(
        self,
        user_id: int,
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        加载用户的项目列表
        
        如果指定了 project_id，只加载该项目;
        否则加载用户拥有的所有活跃项目。
        """
        try:
            if project_id:
                query = select(Project).where(
                    Project.id == project_id,
                    Project.owner_id == user_id
                )
            else:
                query = select(Project).where(
                    Project.owner_id == user_id,
                    Project.status == "active"
                ).order_by(
                    desc(Project.updated_at)
                ).limit(self.MAX_PROJECTS)
            
            result = await self.db.execute(query)
            projects = result.scalars().all()
            
            project_list = []
            for p in projects:
                # 统计每个项目的任务数
                task_counts = await self._count_project_tasks(p.id)
                project_list.append({
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    **task_counts,
                })
            
            return project_list
            
        except Exception as e:
            print(f"⚠️ 加载项目列表失败: {e}")
            return []
    
    async def _count_project_tasks(self, project_id: int) -> Dict[str, int]:
        """统计项目的任务数量"""
        try:
            result = await self.db.execute(
                select(Task).where(Task.project_id == project_id)
            )
            tasks = result.scalars().all()
            
            return {
                "task_count": len(tasks),
                "completed_count": sum(
                    1 for t in tasks if t.status == "completed"
                ),
                "in_progress_count": sum(
                    1 for t in tasks if t.status == "in_progress"
                ),
                "pending_count": sum(
                    1 for t in tasks if t.status == "pending"
                ),
            }
        except Exception:
            return {
                "task_count": 0,
                "completed_count": 0,
                "in_progress_count": 0,
                "pending_count": 0,
            }
    
    async def _load_active_tasks(
        self,
        user_id: int,
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        加载用户最近活跃的任务
        
        优先展示: 进行中 > 待办 > 最近更新
        """
        try:
            query = select(Task).where(
                or_(Task.assignee_id == user_id),
                Task.status.in_(["pending", "in_progress"]),
            )
            
            if project_id:
                query = query.where(Task.project_id == project_id)
            
            query = query.order_by(
                # 进行中的任务优先
                Task.status.desc(),
                # 截止日期紧迫的优先
                Task.due_date.asc().nulls_last(),
                # 最近更新的优先
                Task.updated_at.desc(),
            ).limit(self.MAX_TASKS)
            
            result = await self.db.execute(query)
            tasks = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": (t.description or "")[:100],
                    "status": t.status,
                    "priority": t.priority,
                    "progress": t.progress,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "project_id": t.project_id,
                }
                for t in tasks
            ]
            
        except Exception as e:
            print(f"⚠️ 加载任务列表失败: {e}")
            return []
    
    async def _load_recent_messages(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        加载最近的钉钉对话历史
        
        用于支持"这个任务"、"上面那个"等指代的理解。
        优先从内存中的 dingtalk_conversation_cache 获取，如果没有再尝试获取系统会话。
        """
        try:
            from app.services.cache_service import dingtalk_conversation_cache
            
            # 1. 尝试从钉钉专用内存缓存中获取最近消息
            recent_dingtalk = dingtalk_conversation_cache.get_messages(user_id)
            if recent_dingtalk:
                return [
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")[:200],  # 截断长消息
                    }
                    for msg in recent_dingtalk[-self.MAX_RECENT_MESSAGES:]
                ]
            
            # 2. 如果内存中没有，回退到系统 AIConversation (主要用于刚启动或清理缓存后)
            # 查找用户最近的对话
            result = await self.db.execute(
                select(AIConversation).where(
                    AIConversation.user_id == user_id
                ).order_by(
                    desc(AIConversation.updated_at)
                ).limit(1)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                return []
            
            # 获取最近的消息
            messages = conversation.messages_list
            if not messages:
                return []
            
            # 返回最近 N 条消息
            recent = messages[-self.MAX_RECENT_MESSAGES:]
            return [
                {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")[:200],  # 截断长消息
                }
                for msg in recent
            ]
            
        except Exception as e:
            print(f"⚠️ 加载对话历史失败: {e}")
            return []
    
    def _compute_stats(self, tasks: List[Dict]) -> Dict[str, Any]:
        """计算任务统计信息"""
        if not tasks:
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "pending": 0,
                "overdue": 0,
            }
        
        now = datetime.now(timezone.utc)
        overdue_count = 0
        
        for t in tasks:
            if t.get("due_date") and t.get("status") != "completed":
                try:
                    due = datetime.fromisoformat(
                        t["due_date"].replace("Z", "+00:00")
                    )
                    if due < now:
                        overdue_count += 1
                except (ValueError, TypeError):
                    pass
        
        return {
            "total": len(tasks),
            "completed": sum(
                1 for t in tasks if t.get("status") == "completed"
            ),
            "in_progress": sum(
                1 for t in tasks if t.get("status") == "in_progress"
            ),
            "pending": sum(
                1 for t in tasks if t.get("status") == "pending"
            ),
            "overdue": overdue_count,
        }
