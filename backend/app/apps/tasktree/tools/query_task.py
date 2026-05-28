from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import Task, Project
from datetime import datetime

class QueryTaskSchema(BaseModel):
    status: Optional[str] = Field(None, description="任务状态筛选: pending/in_progress/completed/archived")
    priority: Optional[str] = Field(None, description="优先级筛选: low/medium/high/urgent")
    due_date_start: Optional[str] = Field(None, description="查询截止日期的起始点 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    due_date_end: Optional[str] = Field(None, description="查询截止日期的结束点 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    limit: int = Field(30, description="返回的最大记录数")

class QueryTaskTool(BaseTool):
    name = "query_task_tool"
    description = "查询当前用户的任务列表，支持按状态和优先级过滤"
    parameters_schema = QueryTaskSchema

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        status = kwargs.get("status")
        priority = kwargs.get("priority")
        due_date_start = kwargs.get("due_date_start")
        due_date_end = kwargs.get("due_date_end")
        limit = kwargs.get("limit", 30)

        # 构建查询条件 (确保只查当前用户的任务)
        stmt = select(Task).join(Project).where(Project.owner_id == user_id)
        
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
            
        if due_date_start:
            try:
                dt_start = datetime.strptime(due_date_start, "%Y-%m-%d %H:%M:%S") if len(due_date_start) > 10 else datetime.strptime(due_date_start, "%Y-%m-%d")
                stmt = stmt.where(Task.due_date >= dt_start)
            except Exception as e:
                print(f"解析 due_date_start 失败: {e}")
                
        if due_date_end:
            try:
                dt_end = datetime.strptime(due_date_end, "%Y-%m-%d %H:%M:%S") if len(due_date_end) > 10 else datetime.strptime(due_date_end, "%Y-%m-%d")
                stmt = stmt.where(Task.due_date <= dt_end)
            except Exception as e:
                print(f"解析 due_date_end 失败: {e}")
            
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()
        
        if not tasks:
            return ToolResult(
                success=True,
                output="未找到符合条件的任务。",
                data={"tasks": []}
            )
            
        # 格式化输出给 LLM 看的上下文
        output_lines = [f"找到 {len(tasks)} 个任务:"]
        task_data = []
        for t in tasks:
            due_str = t.due_date.strftime("%Y-%m-%d %H:%M") if getattr(t, 'due_date', None) else "无"
            line = f"- [{t.status}] ID:{t.id} {t.name} (优先级: {t.priority}, 截止: {due_str})"
            output_lines.append(line)
            task_data.append({
                "id": t.id,
                "name": t.name,
                "status": t.status,
                "priority": t.priority,
                "due_date": due_str
            })
            
        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data={"tasks": task_data}
        )
