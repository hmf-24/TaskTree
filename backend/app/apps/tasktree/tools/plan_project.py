from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.project_planner import ProjectPlanner

class PlanProjectSchema(BaseModel):
    project_name: str = Field(..., description="要规划的项目名称或主题")
    goal: str = Field(..., description="项目的最终目标描述")
    constraints: Optional[str] = Field(None, description="限制条件，例如时间或资源")

class PlanProjectTool(BaseTool):
    name = "plan_project_tool"
    description = "创建一个新项目，并自动生成任务拆解和排期规划"
    parameters_schema = PlanProjectSchema

    def __init__(self, db: AsyncSession, llm_service):
        self.db = db
        self.llm_service = llm_service

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        project_name = kwargs.get("project_name")
        goal = kwargs.get("goal")
        constraints = kwargs.get("constraints", "")
        
        # 复用已有的 ProjectPlanner 逻辑，但将其封装为 Tool
        planner = ProjectPlanner(self.db, self.llm_service)
        try:
            # 这是一个耗时操作
            result = await planner.plan_project(
                user_id=user_id,
                project_name=project_name,
                description=f"目标: {goal}\n限制: {constraints}"
            )
            
            return ToolResult(
                success=True,
                output=f"项目 '{project_name}' 规划成功并已保存到数据库。\n\n{result.get('message', '')}",
                data=result.get('data')
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=f"规划项目失败: {str(e)}"
            )
