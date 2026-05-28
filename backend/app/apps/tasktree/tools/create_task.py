from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Task, Project
from datetime import datetime

class CreateTaskSchema(BaseModel):
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    priority: str = Field("medium", description="优先级: low/medium/high/urgent")
    estimated_time: Optional[float] = Field(None, description="预估时间（小时）")
    project_id: Optional[int] = Field(None, description="所属项目ID，如果未提供将自动使用默认项目")
    due_date: Optional[str] = Field(None, description="截止日期，格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS")

class CreateTaskTool(BaseTool):
    name = "create_task_tool"
    description = "创建一个新任务"
    parameters_schema = CreateTaskSchema

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        name = kwargs.get("name")
        description = kwargs.get("description")
        priority = kwargs.get("priority", "medium")
        estimated_time = kwargs.get("estimated_time")
        project_id = kwargs.get("project_id")
        due_date_str = kwargs.get("due_date")
        parsed_due_date = None
        if due_date_str:
            try:
                if len(due_date_str) == 10:
                    parsed_due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                else:
                    parsed_due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"解析 due_date 失败: {e}")

        # 如果没有指定项目，查找用户的默认收集箱项目
        if not project_id:
            stmt = select(Project).where(Project.owner_id == user_id, Project.name == "收集箱")
            result = await self.db.execute(stmt)
            default_project = result.scalars().first()
            if not default_project:
                # 自动创建一个默认收集箱项目
                default_project = Project(
                    name="收集箱",
                    description="自动创建的默认项目，用于归档未分类的任务。",
                    owner_id=user_id,
                    status="active"
                )
                self.db.add(default_project)
                await self.db.commit()
                await self.db.refresh(default_project)
            project_id = default_project.id

        # 检查项目是否存在及权限
        stmt = select(Project).where(Project.id == project_id, Project.owner_id == user_id)
        result = await self.db.execute(stmt)
        if not result.scalars().first():
            return ToolResult(
                success=False,
                output=f"创建失败：找不到 ID 为 {project_id} 的项目或无权限。"
            )

        new_task = Task(
            name=name,
            description=description,
            priority=priority,
            estimated_time=estimated_time,
            project_id=project_id,
            status="pending",
            due_date=parsed_due_date
        )
        self.db.add(new_task)
        await self.db.commit()
        await self.db.refresh(new_task)
        
        from app.services.cache_service import user_task_list_cache
        user_task_list_cache.delete_tasks(user_id)

        return ToolResult(
            success=True,
            output=f"成功创建任务 [{new_task.id}] {new_task.name}",
            data={
                "id": new_task.id,
                "name": new_task.name,
                "project_id": new_task.project_id
            }
        )
