"""
TaskTree AI 对话管理路由
========================
提供 AI 对话历史管理、消息发送、任务分析、任务修改、项目规划等端点。
所有操作都通过 get_current_user 进行身份验证。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.models import User
from app.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    AIMessageResponse,
    AnalyzeRequest,
    ModifyRequest,
    PlanRequest,
    MessageResponse,
    MessageSchema
)
from app.api.v1.auth import get_current_user
from app.services.ai_conversation_service import (
    AIConversationService,
    LLMError,
    LLMTimeoutError,
    LLMAuthError,
    LLMRateLimitError
)
from app.services.task_analyzer import TaskAnalyzer
from app.services.task_modifier import TaskModifier
from app.services.project_planner import ProjectPlanner
from app.services.llm_service import LLMService

router = APIRouter()


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    return LLMService()


@router.post("/conversations", response_model=MessageResponse)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """创建新对话"""
    try:
        # 验证对话类型
        valid_types = ['create', 'analyze', 'modify', 'plan']
        if request.conversation_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的对话类型,必须是: {', '.join(valid_types)}"
            )
        
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 创建对话
        conversation = await conversation_service.create_conversation(
            user_id=current_user.id,
            project_id=request.project_id,
            conversation_type=request.conversation_type,
            initial_message=request.initial_message
        )
        
        # 构建响应
        messages = [
            MessageSchema(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                actions=msg.get("actions")
            )
            for msg in conversation.messages_list
        ]
        
        response_data = ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            project_id=conversation.project_id,
            task_id=conversation.task_id,
            conversation_type=conversation.conversation_type,
            title=conversation.title,
            messages=messages,
            context_data=conversation.context_dict,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
        return MessageResponse(
            code=201,
            message="创建对话成功",
            data=response_data.model_dump()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建对话失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """发送消息"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 发送消息
        result = await conversation_service.send_message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            user_message=request.content
        )
        
        # 构建响应
        response_data = AIMessageResponse(
            reply=result["reply"],
            conversation_id=result["conversation_id"],
            message_count=result["message_count"]
        )
        
        return MessageResponse(
            message="发送消息成功",
            data=response_data.model_dump()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except LLMAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except LLMRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {str(e)}"
        )


@router.get("/conversations", response_model=MessageResponse)
async def list_conversations(
    project_id: Optional[int] = None,
    conversation_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """获取对话列表"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 获取对话列表
        conversations = await conversation_service.list_conversations(
            user_id=current_user.id,
            project_id=project_id,
            conversation_type=conversation_type
        )
        
        # 构建响应
        response_data = [
            ConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                project_id=conv.project_id,
                task_id=conv.task_id,
                conversation_type=conv.conversation_type,
                title=conv.title,
                messages=[
                    MessageSchema(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg["timestamp"],
                        actions=msg.get("actions")
                    )
                    for msg in conv.messages_list
                ],
                context_data=conv.context_dict,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            ).model_dump()
            for conv in conversations
        ]
        
        return MessageResponse(
            message="获取对话列表成功",
            data=response_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=MessageResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """获取对话详情"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 获取对话
        conversation = await conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 构建响应
        response_data = ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            project_id=conversation.project_id,
            task_id=conversation.task_id,
            conversation_type=conversation.conversation_type,
            title=conversation.title,
            messages=[
                MessageSchema(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg["timestamp"],
                    actions=msg.get("actions")
                )
                for msg in conversation.messages_list
            ],
            context_data=conversation.context_dict,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
        return MessageResponse(
            message="获取对话详情成功",
            data=response_data.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话详情失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/analyze", response_model=MessageResponse)
async def analyze_tasks(
    conversation_id: int,
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """任务分析"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 验证对话存在且属于当前用户
        conversation = await conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 创建任务分析器
        task_analyzer = TaskAnalyzer(db, llm_service)
        
        # 执行分析
        analysis_result = await task_analyzer.analyze_project_tasks(
            project_id=conversation.project_id,
            user_id=current_user.id,
            focus_areas=request.focus_areas
        )
        
        # 将分析结果添加到对话历史
        analysis_message = f"""## 任务分析结果

**整体评估**: {analysis_result['summary']}

**风险评分**: {analysis_result['risk_score']}/100

"""
        
        if analysis_result['issues']:
            analysis_message += "### 发现的问题\n\n"
            for issue in analysis_result['issues']:
                analysis_message += f"- **{issue['type']}** ({issue['severity']}): {issue['description']}\n"
                analysis_message += f"  - 建议: {issue['suggestion']}\n"
                analysis_message += f"  - 相关任务: {', '.join(f'#{tid}' for tid in issue['task_ids'])}\n\n"
        
        if analysis_result['recommendations']:
            analysis_message += "### 优化建议\n\n"
            for rec in analysis_result['recommendations']:
                analysis_message += f"- **{rec['action']}** (任务 #{rec['task_id']}): {rec['details']}\n"
        
        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=analysis_message
        )
        
        return MessageResponse(
            message="任务分析完成",
            data=analysis_result
        )
        
    except HTTPException:
        raise
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务分析失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/modify", response_model=MessageResponse)
async def modify_tasks(
    conversation_id: int,
    request: ModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """任务修改"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 验证对话存在且属于当前用户
        conversation = await conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 创建任务修改器
        task_modifier = TaskModifier(db, llm_service)
        
        # 执行修改
        modification_result = await task_modifier.execute_modification(
            modification=request.modification
        )
        
        # 将修改结果添加到对话历史
        result_message = f"""## 任务修改结果

**总计**: {modification_result['total']} 个任务
**成功**: {modification_result['success_count']} 个
**失败**: {modification_result['failed_count']} 个

"""
        
        if modification_result['results']['success']:
            result_message += f"**成功修改的任务**: {', '.join(f'#{tid}' for tid in modification_result['results']['success'])}\n\n"
        
        if modification_result['results']['errors']:
            result_message += "**错误信息**:\n"
            for error in modification_result['results']['errors']:
                result_message += f"- {error}\n"
        
        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result_message
        )
        
        return MessageResponse(
            message="任务修改完成",
            data=modification_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务修改失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/plan", response_model=MessageResponse)
async def plan_project(
    conversation_id: int,
    request: PlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """项目规划"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 验证对话存在且属于当前用户
        conversation = await conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 创建项目规划器
        project_planner = ProjectPlanner(db, llm_service)
        
        # 执行规划
        planning_result = await project_planner.analyze_and_plan(
            project_id=conversation.project_id,
            user_id=current_user.id,
            planning_goal=request.planning_goal
        )
        
        # 将规划结果添加到对话历史
        planning_message = f"""## 项目规划建议

**规划摘要**: {planning_result['summary']}

"""
        
        if planning_result['missing_tasks']:
            planning_message += "### 建议添加的任务\n\n"
            for task in planning_result['missing_tasks']:
                planning_message += f"**{task['name']}** ({task['priority']})\n"
                planning_message += f"- 描述: {task['description']}\n"
                planning_message += f"- 原因: {task['reason']}\n"
                if task.get('estimated_time'):
                    planning_message += f"- 预计时间: {task['estimated_time']} 分钟\n"
                planning_message += "\n"
        
        if planning_result['structure_improvements']:
            planning_message += "### 结构改进建议\n\n"
            for improvement in planning_result['structure_improvements']:
                planning_message += f"- **问题**: {improvement['issue']}\n"
                planning_message += f"  **建议**: {improvement['suggestion']}\n\n"
        
        if planning_result['milestones']:
            planning_message += "### 里程碑建议\n\n"
            for milestone in planning_result['milestones']:
                planning_message += f"- **{milestone['name']}** (目标日期: {milestone['target_date']})\n"
                if milestone.get('tasks'):
                    planning_message += f"  相关任务: {', '.join(f'#{tid}' for tid in milestone['tasks'])}\n"
                planning_message += "\n"
        
        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=planning_message
        )
        
        return MessageResponse(
            message="项目规划完成",
            data=planning_result
        )
        
    except HTTPException:
        raise
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"项目规划失败: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}", response_model=MessageResponse)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """删除对话"""
    try:
        # 创建对话服务
        conversation_service = AIConversationService(db, llm_service)
        
        # 删除对话
        success = await conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        return MessageResponse(
            message="删除对话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对话失败: {str(e)}"
        )
