import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models import User, UserNotificationSettings, Project, ProjectMember
from app.schemas import (
    MessageResponse, 
    ClarifyTaskRequest, 
    DecomposeTaskRequest
)
from app.api.v1.auth import get_current_user
from app.services.llm_service import LLMService

router = APIRouter()

async def get_user_llm_service(user_id: int, db: AsyncSession) -> LLMService:
    """获取用户的 LLM 服务实例"""
    result = await db.execute(
        select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings or not settings.llm_provider:
        raise HTTPException(
            status_code=400, 
            detail="未配置大模型服务。请先在【设置 → 智能提醒】中配置大模型提供商和 API Key。"
        )
    
    # 解密 API Key
    from app.core.crypto import decrypt_api_key
    api_key = decrypt_api_key(settings.llm_api_key_encrypted) if settings.llm_api_key_encrypted else None
    
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="未配置大模型 API Key。请先在【设置 → 智能提醒】中配置。"
        )
        
    return LLMService(
        provider=settings.llm_provider,
        api_key=api_key,
        model=settings.llm_model,
        group_id=settings.llm_group_id
    )

async def check_project_access(project_id: int, user_id: int, db: AsyncSession):
    """验证项目权限"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    if project.owner_id != user_id:
        result = await db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="没有权限访问该项目")


@router.post("/llm_tasks/clarify", response_model=MessageResponse)
async def clarify_task(
    request: ClarifyTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """通过多轮对话澄清任务需求"""
    await check_project_access(request.project_id, current_user.id, db)
    
    try:
        llm_service = await get_user_llm_service(current_user.id, db)
    except HTTPException as e:
        raise e
    
    system_prompt = (
        "你是一个资深产品经理和项目管理专家。用户正在创建一个新任务，你需要帮助用户明确任务目标、范围和验收标准。\n\n"
        "你的职责：\n"
        "1. 如果用户的描述过于简略或模糊，提出1-2个具体问题引导用户补充细节\n"
        "2. 关注：功能边界、UI/UX要求、技术约束、验收标准\n"
        "3. 如果用户的描述已经足够清晰（包含目标、范围、验收标准），回复：'需求已足够清晰，可以进行任务分解'\n\n"
        "注意：\n"
        "- 保持专业、简练，每次只问1-2个最关键的问题\n"
        "- 不要问太多细节，避免让用户感到繁琐\n"
        "- 用中文回复，语气友好专业"
    )
    
    # 构造对话历史
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})
        
    try:
        response = await llm_service.chat(messages=messages, temperature=0.7, max_tokens=1000)
        return MessageResponse(data={"reply": response})
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(status_code=504, detail="LLM 服务响应超时，请稍后重试")
        elif "401" in error_msg or "403" in error_msg:
            raise HTTPException(status_code=400, detail="API Key 无效或已过期，请检查配置")
        elif "429" in error_msg:
            raise HTTPException(status_code=429, detail="API 调用频率超限，请稍后重试")
        else:
            raise HTTPException(status_code=500, detail=f"LLM 调用失败: {error_msg}")


@router.post("/llm_tasks/decompose", response_model=MessageResponse)
async def decompose_task(
    request: DecomposeTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """对明确的需求进行子任务拆解"""
    await check_project_access(request.project_id, current_user.id, db)
    
    try:
        llm_service = await get_user_llm_service(current_user.id, db)
    except HTTPException as e:
        raise e
    
    system_prompt = (
        "你是一个资深研发经理。请根据用户提供的任务需求，将其拆解为3-8个具体、可执行的子任务，并为每个任务规划时间。\n\n"
        "要求：\n"
        "1. 每个子任务应该是独立、可执行的工作单元\n"
        "2. 子任务应该按照合理的执行顺序排列\n"
        "3. 任务名称简洁明确（10字以内）\n"
        "4. 描述要具体，包含关键的技术细节或验收标准\n"
        "5. 为每个任务估算工时（estimated_hours，单位:小时）\n"
        "6. 根据任务顺序规划开始日期和截止日期（格式:YYYY-MM-DD）\n\n"
        "你必须只返回一个 JSON 数组，不要返回其他任何内容（不要 markdown 标记，不要额外说明）。\n"
        "JSON 数组中每个元素包含:\n"
        "- name: 子任务名称（简洁明确）\n"
        "- description: 详细描述（包含技术细节和验收标准）\n"
        "- priority: 优先级（low/medium/high/urgent）\n"
        "- estimated_hours: 预估工时（数字，单位:小时）\n"
        "- start_date: 建议开始日期（YYYY-MM-DD格式，从今天开始规划）\n"
        "- due_date: 建议截止日期（YYYY-MM-DD格式，考虑工时和依赖关系）\n\n"
        "示例输出：\n"
        '[{"name": "设计数据库表", "description": "设计 user 和 profile 表结构，包含字段类型、索引和外键约束", "priority": "high"},'
        '{"name": "实现用户注册API", "description": "POST /api/register 接口，支持邮箱注册，返回 JWT token", "priority": "high"}]'
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"任务需求：\n{request.requirement}"}
    ]
    
    try:
        response = await llm_service.chat(messages=messages, temperature=0.3, max_tokens=2000)
        
        # 尝试解析 JSON
        raw_text = response.strip()
        
        # 清除可能的 markdown code block 标记
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        
        raw_text = raw_text.strip()
        
        try:
            subtasks = json.loads(raw_text)
            if not isinstance(subtasks, list):
                subtasks = [subtasks]
            
            # 验证每个子任务的格式
            valid_subtasks = []
            for task in subtasks:
                if isinstance(task, dict) and "name" in task:
                    valid_subtasks.append({
                        "name": task.get("name", "未命名任务"),
                        "description": task.get("description", ""),
                        "priority": task.get("priority", "medium") if task.get("priority") in ["low", "medium", "high", "urgent"] else "medium",
                        "estimated_hours": task.get("estimated_hours"),
                        "start_date": task.get("start_date"),
                        "due_date": task.get("due_date")
                    })
            
            if not valid_subtasks:
                raise HTTPException(status_code=500, detail="大模型返回的任务格式不正确")
                
            return MessageResponse(data={"subtasks": valid_subtasks})
            
        except json.JSONDecodeError as e:
            # JSON 解析失败，返回更友好的错误信息
            raise HTTPException(
                status_code=500, 
                detail=f"大模型未返回有效的 JSON 格式。原始响应：{raw_text[:200]}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(status_code=504, detail="LLM 服务响应超时，请稍后重试")
        elif "401" in error_msg or "403" in error_msg:
            raise HTTPException(status_code=400, detail="API Key 无效或已过期，请检查配置")
        elif "429" in error_msg:
            raise HTTPException(status_code=429, detail="API 调用频率超限，请稍后重试")
        else:
            raise HTTPException(status_code=500, detail=f"LLM 调用失败: {error_msg}")
