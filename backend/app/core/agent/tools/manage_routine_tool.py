from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.core.agent.tool import BaseTool, ToolResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.routine import AgentRoutine
from app.services.scheduler_service import scheduler_service
import json

class ManageRoutineSchema(BaseModel):
    action: str = Field(..., description="操作类型，可选值: 'create' (新建), 'list' (列表), 'toggle' (启用/停用), 'delete' (删除)")
    routine_id: Optional[int] = Field(None, description="要操作的任务 ID，用于 toggle 和 delete")
    name: Optional[str] = Field(None, description="任务名称，用于 create")
    schedule_cron: Optional[str] = Field(None, description="Cron 表达式，用于 create，例如 '0 9 * * *' 代表每天早 9 点")
    prompt_template: Optional[str] = Field(None, description="任务的执行指令 (Prompt)，用于 create")
    is_active: Optional[bool] = Field(None, description="是否启用任务，用于 toggle")
    app_source: Optional[str] = Field("tasktree", description="任务所属应用上下文，'tasktree' 或 'readhub'")

class ManageRoutineTool(BaseTool):
    name = "manage_routine_tool"
    description = "管理自动化定时任务 (Routines)。可以将用户的自然语言调度需求（如每天早八点拉取新闻）转化为 Cron 表达式，并保存为后台任务。"
    parameters_schema = ManageRoutineSchema

    def __init__(self, db: AsyncSession, app_source: str):
        self.db = db
        self.app_source = app_source

    async def execute(self, user_id: int, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        
        if action == "list":
            result = await self.db.execute(
                select(AgentRoutine).where(
                    AgentRoutine.user_id == user_id,
                    AgentRoutine.app_source == self.app_source
                )
            )
            routines = result.scalars().all()
            if not routines:
                return ToolResult(success=True, output="您当前没有配置任何自动化定时任务。")
            
            items = []
            for r in routines:
                status = "启用" if r.is_active else "已停用"
                items.append(f"#{r.id} [{status}] {r.name} - 规则: {r.schedule_cron} - 指令: {r.prompt_template[:20]}...")
            return ToolResult(success=True, output="您的自动化定时任务列表:\n" + "\n".join(items))
            
        elif action == "create":
            name = kwargs.get("name")
            cron = kwargs.get("schedule_cron")
            prompt = kwargs.get("prompt_template")
            app_source = kwargs.get("app_source", self.app_source)
            
            if not all([name, cron, prompt]):
                return ToolResult(success=False, output="新建任务失败：缺少必要的参数 (name, schedule_cron, prompt_template)")
            
            routine = AgentRoutine(
                user_id=user_id,
                app_source=app_source,
                name=name,
                schedule_cron=cron,
                prompt_template=prompt,
                is_active=True
            )
            self.db.add(routine)
            await self.db.commit()
            await self.db.refresh(routine)
            
            # 通知调度器重载
            await scheduler_service.reload_user_routine(routine.id)
            
            return ToolResult(success=True, output=f"已成功创建自动化定时任务 `#{routine.id} {routine.name}`，将按照规则 `{routine.schedule_cron}` 准时执行！")
            
        elif action == "toggle":
            r_id = kwargs.get("routine_id")
            is_active = kwargs.get("is_active")
            if r_id is None or is_active is None:
                return ToolResult(success=False, output="切换状态失败：缺少 routine_id 或 is_active 参数")
                
            res = await self.db.execute(select(AgentRoutine).where(
                AgentRoutine.id == r_id, 
                AgentRoutine.user_id == user_id,
                AgentRoutine.app_source == self.app_source
            ))
            routine = res.scalar_one_or_none()
            if not routine:
                return ToolResult(success=False, output=f"越权或找不到 ID 为 {r_id} 的本机器人专属任务")
                
            routine.is_active = is_active
            await self.db.commit()
            
            if is_active:
                await scheduler_service.reload_user_routine(routine.id)
                msg = f"任务 `#{routine.id}` 已启用并加载"
            else:
                job_id = f"routine_{routine.id}"
                if scheduler_service._scheduler and scheduler_service._scheduler.get_job(job_id):
                    scheduler_service._scheduler.remove_job(job_id)
                msg = f"任务 `#{routine.id}` 已停用"
                
            return ToolResult(success=True, output=msg)
            
        elif action == "delete":
            r_id = kwargs.get("routine_id")
            if r_id is None:
                return ToolResult(success=False, output="删除失败：缺少 routine_id 参数")
                
            res = await self.db.execute(select(AgentRoutine).where(
                AgentRoutine.id == r_id, 
                AgentRoutine.user_id == user_id,
                AgentRoutine.app_source == self.app_source
            ))
            routine = res.scalar_one_or_none()
            if not routine:
                return ToolResult(success=False, output=f"越权或找不到 ID 为 {r_id} 的本机器人专属任务")
                
            # 先从调度器移除
            job_id = f"routine_{routine.id}"
            if scheduler_service._scheduler and scheduler_service._scheduler.get_job(job_id):
                scheduler_service._scheduler.remove_job(job_id)
                
            await self.db.delete(routine)
            await self.db.commit()
            return ToolResult(success=True, output=f"任务 `#{r_id}` 已成功删除")
            
        else:
            return ToolResult(success=False, output=f"未知的操作类型: {action}")
