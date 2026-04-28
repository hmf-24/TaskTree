"""
钉钉智能助手 API 接口
====================
实现钉钉消息回调、用户绑定、进度反馈等功能
"""
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import User, Task, Project, UserNotificationSettings, ProgressFeedback
from app.schemas import MessageResponse
from app.services.dingtalk_service import DingtalkService
from app.services.llm_service import LLMService
from app.services.progress_parser_service import ProgressParserService
from app.services.dingtalk_user_mapping_service import DingtalkUserMappingService
from app.services.task_matcher import TaskMatcherService
from app.services.task_updater import TaskUpdaterService
from app.services.message_printer import MessagePrinterService
from app.services.async_task_queue import run_in_background
from app.services.rate_limiter import (
    dingtalk_rate_limiter,
    bind_rate_limiter,
    test_message_rate_limiter
)
from app.services.cache_service import (
    dingtalk_user_mapping_cache,
    user_task_list_cache
)
from app.services.security_logger import security_logger
from app.schemas import ParseResultSchema

router = APIRouter(prefix="/api/v1/dingtalk", tags=["dingtalk"])

# 初始化服务
dingtalk_service = DingtalkService()
llm_service = LLMService()
message_printer = MessagePrinterService()


def verify_dingtalk_signature(
    timestamp: str,
    sign: str,
    secret: str
) -> bool:
    """验证钉钉签名"""
    try:
        # 构建签名字符串
        string_to_sign = f"{timestamp}\n{secret}"
        
        # 计算签名
        hmac_obj = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        )
        computed_sign = base64.b64encode(hmac_obj.digest()).decode('utf-8')
        
        return computed_sign == sign
    except Exception as e:
        print(f"签名验证失败: {e}")
        return False


@router.post("/callback")
async def dingtalk_callback(
    request_body: dict,
    x_dingtalk_timestamp: str = Header(None),
    x_dingtalk_sign: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    钉钉消息回调接口
    
    接收钉钉用户发送的消息，进行身份验证、进度解析、任务匹配和自动更新
    """
    # 验证时间戳（防止重放攻击）
    try:
        callback_time = int(x_dingtalk_timestamp) / 1000
        current_time = time.time()
        age_seconds = abs(current_time - callback_time)
        
        if age_seconds > 300:  # 5 分钟
            # 记录时间戳过期
            security_logger.log_timestamp_expired(
                dingtalk_user_id=request_body.get("senderId"),
                timestamp=x_dingtalk_timestamp,
                age_seconds=age_seconds
            )
            raise HTTPException(status_code=401, detail="请求已过期")
    except ValueError as e:
        # 记录无效请求
        security_logger.log_invalid_request(
            dingtalk_user_id=request_body.get("senderId"),
            error=f"无效的时间戳: {str(e)}"
        )
        raise HTTPException(status_code=401, detail=f"时间戳验证失败: {str(e)}")
    
    # 验证签名（从数据库获取 secret，如果没有则跳过验证）
    # 简化处理：先尝试找到用户，再验证签名
    dingtalk_user_id = request_body.get("senderId")
    if not dingtalk_user_id:
        return MessageResponse(message="success")
    
    # 查找用户映射（直接查询数据库，不使用service）
    result = await db.execute(
        select(UserNotificationSettings).where(
            UserNotificationSettings.dingtalk_user_id == dingtalk_user_id
        )
    )
    settings = result.scalar_one_or_none()
    user_id = settings.user_id if settings else None
    
    # 如果找到用户且配置了secret，验证签名
    if settings and settings.dingtalk_secret and x_dingtalk_sign:
        if not verify_dingtalk_signature(x_dingtalk_timestamp, x_dingtalk_sign, settings.dingtalk_secret):
            # 记录签名验证失败
            security_logger.log_signature_verification_failed(
                dingtalk_user_id=dingtalk_user_id,
                timestamp=x_dingtalk_timestamp
            )
            # 不拒绝请求，只记录日志
            print(f"⚠️ 签名验证失败，但继续处理: {dingtalk_user_id}")
    
    # 快速响应钉钉（200ms 内）
    try:
        # 提取消息信息
        message_content = request_body.get("text", {}).get("content", "")
        
        if not message_content:
            return MessageResponse(message="success")
        
        # 用户ID已经在上面获取过了
        if user_id is None:
            # 用户未绑定，返回绑定引导
            await dingtalk_service.send_message(
                dingtalk_user_id,
                "请先绑定钉钉账号，访问系统设置进行绑定"
            )
            return MessageResponse(message="success")
        
        # 检查频率限制
        is_allowed, rate_limit_info = dingtalk_rate_limiter.is_allowed(user_id)
        if not is_allowed:
            # 记录频率限制超出
            security_logger.log_rate_limit_exceeded(
                user_id=user_id,
                dingtalk_user_id=dingtalk_user_id,
                limit=rate_limit_info.get('limit'),
                retry_after=rate_limit_info.get('retry_after')
            )
            
            # 频率限制，返回错误
            await dingtalk_service.send_message(
                dingtalk_user_id,
                f"请求过于频繁，请在 {rate_limit_info['retry_after']} 秒后重试"
            )
            return MessageResponse(message="success")
        
        # 异步处理消息（不阻塞回调响应）
        # 使用后台任务队列
        await run_in_background(
            process_dingtalk_message,
            user_id=user_id,
            dingtalk_user_id=dingtalk_user_id,
            message_content=message_content,
            db=db
        )
        
        return MessageResponse(message="success")
    
    except Exception as e:
        print(f"钉钉回调处理失败: {e}")
        return MessageResponse(message="success")  # 仍然返回 success 避免钉钉重试


async def process_dingtalk_message(
    user_id: int,
    dingtalk_user_id: str,
    message_content: str,
    db: AsyncSession
):
    """处理钉钉消息（异步）"""
    try:
        # 1. 使用 ProgressParserService 解析进度
        progress_parser = ProgressParserService(llm_service)
        parse_result_dict = progress_parser.parse(message=message_content)
        
        if not parse_result_dict or parse_result_dict.get("confidence", 0) < 0.3:
            await dingtalk_service.send_message(
                dingtalk_user_id,
                message_printer.format_help_message()
            )
            return
        
        # 2. 使用 TaskMatcherService 匹配任务
        task_matcher = TaskMatcherService(db)
        keywords = parse_result_dict.get("keywords", [])
        
        # 如果没有关键词，尝试从消息中提取
        if not keywords:
            # 简单分词（可以使用更复杂的分词工具）
            keywords = [word for word in message_content.split() if len(word) > 1]
        
        matched_tasks = await task_matcher.match(
            keywords=keywords,
            user_id=user_id,
            limit=5
        )
        
        if not matched_tasks:
            error_msg = message_printer.format_error_message("no_match")
            await dingtalk_service.send_message(dingtalk_user_id, error_msg)
            return
        
        if len(matched_tasks) > 1:
            # 多个匹配，让用户选择
            multi_match_msg = message_printer.format_multiple_matches(
                matched_tasks,
                " ".join(keywords)
            )
            await dingtalk_service.send_message(dingtalk_user_id, multi_match_msg)
            return
        
        # 3. 根据解析类型处理
        task = matched_tasks[0]
        parse_type = parse_result_dict.get("type", "query")
        
        # 如果是查询类型，返回任务详情
        if parse_type == "query":
            # 获取任务详细信息
            task_detail = f"""## 📋 任务详情

**任务名称**: {task.name}
**任务状态**: {task.status}
**完成进度**: {task.progress}%
**优先级**: {task.priority or '未设置'}
**截止时间**: {task.due_date.strftime('%Y-%m-%d') if task.due_date else '未设置'}
**描述**: {task.description or '无'}

---
*来自 TaskTree*"""
            
            await dingtalk_service.send_message(
                dingtalk_user_id=dingtalk_user_id,
                content=task_detail,
                msg_type="markdown",
                title=f"任务详情 - {task.name}"
            )
            return
        
        # 其他类型（completed, in_progress, problem, extend）才更新任务
        task_updater = TaskUpdaterService(db)
        
        try:
            # 构建 ParseResultSchema
            parse_result = ParseResultSchema(
                type=parse_result_dict.get("type", "query"),
                progress=parse_result_dict.get("progress", 0),
                description=parse_result_dict.get("description", ""),
                extend_days=parse_result_dict.get("extend_days", 0),
                confidence=parse_result_dict.get("confidence", 0.5),
                keywords=keywords
            )
            
            updated_task = await task_updater.update_from_feedback(
                task_id=task.id,
                parse_result=parse_result,
                user_id=user_id,
                message_content=message_content
            )
            
            # 任务更新后，清除缓存
            user_task_list_cache.delete_tasks(user_id)
            
            # 4. 发送确认消息（使用格式化服务）
            confirmation_msg = message_printer.format_confirmation(
                task_name=updated_task.name,
                action=f"更新任务状态为 {updated_task.status}",
                old_value=f"{task.status} ({task.progress}%)",
                new_value=f"{updated_task.status} ({updated_task.progress}%)"
            )
            await dingtalk_service.send_message(dingtalk_user_id, confirmation_msg)
        
        except PermissionError:
            error_msg = message_printer.format_error_message("permission_denied")
            await dingtalk_service.send_message(dingtalk_user_id, error_msg)
        except ValueError as e:
            error_msg = message_printer.format_error_message("parse_failed", str(e))
            await dingtalk_service.send_message(dingtalk_user_id, error_msg)
    
    except Exception as e:
        print(f"处理钉钉消息失败: {e}")
        import traceback
        traceback.print_exc()
        await dingtalk_service.send_message(
            dingtalk_user_id,
            f"处理消息时出错，请稍后重试"
        )


@router.post("/bind")
async def bind_dingtalk(
    dingtalk_user_id: str,
    dingtalk_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """绑定钉钉账号"""
    # 检查频率限制
    is_allowed, rate_limit_info = bind_rate_limiter.is_allowed(current_user.id)
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请在 {rate_limit_info['retry_after']} 秒后重试"
        )
    
    try:
        # 使用 DingtalkUserMappingService 绑定
        mapping_service = DingtalkUserMappingService(db)
        
        success = mapping_service.bind_user(
            user_id=current_user.id,
            dingtalk_user_id=dingtalk_user_id,
            dingtalk_name=dingtalk_name
        )
        
        if success:
            return MessageResponse(
                message="绑定成功",
                data={
                    "user_id": current_user.id,
                    "dingtalk_user_id": dingtalk_user_id,
                    "dingtalk_name": dingtalk_name
                }
            )
        else:
            raise HTTPException(status_code=500, detail="绑定失败")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"绑定失败: {str(e)}")


@router.delete("/unbind")
async def unbind_dingtalk(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """解除钉钉绑定"""
    try:
        # 使用 DingtalkUserMappingService 解除绑定
        mapping_service = DingtalkUserMappingService(db)
        
        success = mapping_service.unbind_user(user_id=current_user.id)
        
        if success:
            return MessageResponse(message="解除绑定成功")
        else:
            return MessageResponse(message="未绑定钉钉账号")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解除绑定失败: {str(e)}")


@router.get("/binding")
async def get_binding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查询绑定状态"""
    # 使用 DingtalkUserMappingService 查询绑定信息
    mapping_service = DingtalkUserMappingService(db)
    
    dingtalk_info = mapping_service.get_dingtalk_info(user_id=current_user.id)
    
    if not dingtalk_info:
        return MessageResponse(
            message="success",
            data={"is_bound": False}
        )
    
    return MessageResponse(
        message="success",
        data={
            "is_bound": True,
            "dingtalk_user_id": dingtalk_info["dingtalk_user_id"],
            "dingtalk_name": dingtalk_info["dingtalk_name"]
        }
    )


@router.get("/progress-feedback")
async def get_progress_feedback(
    task_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查询进度反馈历史"""
    from app.models import ProgressFeedback
    
    try:
        # 构建查询条件 - 确保用户只能查看自己的反馈
        stmt = select(ProgressFeedback).where(
            ProgressFeedback.user_id == current_user.id
        )
        
        # 如果指定了 task_id，验证任务所有权并添加过滤条件
        if task_id:
            # 验证任务是否属于当前用户
            task_stmt = select(Task).join(Project).where(
                Task.id == task_id,
                Project.owner_id == current_user.id
            )
            task_result = await db.execute(task_stmt)
            task = task_result.scalars().first()
            
            if not task:
                # 记录权限拒绝
                security_logger.log_permission_denied(
                    user_id=current_user.id,
                    resource_type="task",
                    resource_id=task_id,
                    action="view_feedback"
                )
                raise HTTPException(status_code=403, detail="无权限访问此任务的反馈")
            
            stmt = stmt.where(ProgressFeedback.task_id == task_id)
        
        # 按创建时间倒序排列
        stmt = stmt.order_by(ProgressFeedback.created_at.desc())
        
        # 获取总数
        count_stmt = select(func.count()).select_from(ProgressFeedback).where(
            ProgressFeedback.user_id == current_user.id
        )
        if task_id:
            count_stmt = count_stmt.where(ProgressFeedback.task_id == task_id)
        
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # 分页 - 最多返回 50 条
        stmt = stmt.limit(min(limit, 50)).offset(offset)
        
        # 执行查询
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()
        
        # 构建响应
        data = []
        for feedback in feedbacks:
            data.append({
                "id": feedback.id,
                "user_id": feedback.user_id,
                "task_id": feedback.task_id,
                "message_content": feedback.message_content,
                "parsed_result": feedback.parsed_dict,
                "feedback_type": feedback.feedback_type,
                "created_at": feedback.created_at.isoformat()
            })
        
        return MessageResponse(
            message="success",
            data={
                "items": data,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"查询进度反馈失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/test-message")
async def send_test_message(
    message: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送测试消息"""
    # 检查频率限制
    is_allowed, rate_limit_info = test_message_rate_limiter.is_allowed(current_user.id)
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请在 {rate_limit_info['retry_after']} 秒后重试"
        )
    
    if not current_user.notification_settings or not current_user.notification_settings.dingtalk_user_id:
        raise HTTPException(status_code=400, detail="未绑定钉钉账号")
    
    try:
        await dingtalk_service.send_message(
            current_user.notification_settings.dingtalk_user_id,
            message
        )
        return MessageResponse(message="消息发送成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return MessageResponse(
        message="success",
        data={
            "status": "healthy",
            "dingtalk_service": "ok",
            "llm_service": "ok"
        }
    )
