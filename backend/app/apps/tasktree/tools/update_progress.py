from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Task, Project, ProgressFeedback
from datetime import datetime

class UpdateProgressSchema(BaseModel):
    task_id: int = Field(..., description="要更新的任务 ID")
    status: Optional[str] = Field(None, description="新状态: pending/in_progress/completed/archived")
    progress: Optional[int] = Field(None, description="进度百分比 0-100")
    message: Optional[str] = Field(None, description="附带的进度说明或问题记录")

class UpdateProgressTool(BaseTool):
    name = "update_progress_tool"
    description = "更新指定任务的状态或进度百分比，并记录反馈"
    parameters_schema = UpdateProgressSchema

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        task_id = kwargs.get("task_id")
        status = kwargs.get("status")
        progress = kwargs.get("progress")
        message = kwargs.get("message", "")

        # 检查任务所有权
        stmt = select(Task).join(Project).where(Task.id == task_id, Project.owner_id == user_id)
        result = await self.db.execute(stmt)
        task = result.scalars().first()
        
        if not task:
            return ToolResult(
                success=False,
                output=f"更新失败：找不到 ID 为 {task_id} 的任务或无权限。"
            )

        old_status = task.status
        old_progress = task.progress

        if status:
            task.status = status
            if status == "completed":
                task.progress = 100
        
        if progress is not None:
            task.progress = progress
            if progress == 100:
                task.status = "completed"
            elif progress > 0 and task.status == "pending":
                task.status = "in_progress"
                
        # 记录反馈
        feedback = ProgressFeedback(
            user_id=user_id,
            task_id=task.id,
            message_content=message or f"状态: {old_status}->{task.status}, 进度: {old_progress}%->{task.progress}%",
            feedback_type="system_tool",
            parsed_dict=kwargs
        )
        self.db.add(feedback)
        await self.db.commit()

        from app.services.cache_service import user_task_list_cache
        user_task_list_cache.delete_tasks(user_id)

        return ToolResult(
            success=True,
            output=f"成功更新任务 [{task.id}] {task.name}。当前状态: {task.status}, 进度: {task.progress}%",
            data={
                "id": task.id,
                "status": task.status,
                "progress": task.progress
            }
        )
