"""
TaskTree 智能提醒设置接口
======================
用户配置钉钉Webhook和自定义提醒规则。
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import User, UserNotificationSettings, NotificationLog
from app.schemas import (
    UserNotificationSettingsCreate,
    UserNotificationSettingsUpdate,
    UserNotificationSettingsResponse,
    MessageResponse
)

router = APIRouter(prefix="/notifications", tags=["智能提醒"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """从 auth 路由导入 get_current_user 函数"""
    from app.api.v1.auth import get_current_user as _get_current_user
    return await _get_current_user(credentials, db)


# 默认提醒规则模板
# 加密工具
from app.core.crypto import encrypt_api_key, decrypt_api_key

DEFAULT_RULES = [
    {
        "id": "due_date_remind",
        "name": "截止时间提醒",
        "enabled": True,
        "condition": "due_date_remind",
        "hours_before": 24,
        "repeat": ["08:00", "20:00"]
    },
    {
        "id": "progress_stalled",
        "name": "进度落后提醒",
        "enabled": True,
        "condition": "progress_stalled",
        "threshold_days": 3,
        "repeat": ["09:00"]
    },
    {
        "id": "overdue_tasks",
        "name": "逾期任务提醒",
        "enabled": True,
        "condition": "overdue_tasks",
        "repeat": ["09:00"]
    },
    {
        "id": "dependency_unblocked",
        "name": "依赖解除提醒",
        "enabled": False,
        "condition": "dependency_unblocked",
        "repeat": ["immediate"]
    }
]


@router.get("/settings", response_model=UserNotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的通知设置"""
    result = await db.execute(
        select(UserNotificationSettings).where(
            UserNotificationSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # 返回默认设置
        return UserNotificationSettingsResponse(
            id=0,
            user_id=current_user.id,
            dingtalk_webhook=None,
            dingtalk_secret=None,
            llm_provider="minmax",
            llm_api_key=None,
            llm_model=None,
            llm_group_id=None,
            rules=DEFAULT_RULES,
            enabled=True,
            daily_limit=5
        )

    # 解析 rules JSON
    rules = json.loads(settings.rules) if settings.rules else DEFAULT_RULES

    # 解密 API Key
    api_key = decrypt_api_key(settings.llm_api_key_encrypted) if settings.llm_api_key_encrypted else None

    return UserNotificationSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        dingtalk_webhook=settings.dingtalk_webhook,
        dingtalk_secret=settings.dingtalk_secret,
        llm_provider=settings.llm_provider,
        llm_api_key=api_key,
        llm_model=settings.llm_model,
        llm_group_id=settings.llm_group_id,
        rules=rules,
        enabled=settings.enabled,
        daily_limit=settings.daily_limit
    )


@router.post("/settings", response_model=MessageResponse)
async def create_or_update_settings(
    settings_data: UserNotificationSettingsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建或更新用户的通知设置"""
    result = await db.execute(
        select(UserNotificationSettings).where(
            UserNotificationSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()

    rules_json = json.dumps(settings_data.rules or DEFAULT_RULES, ensure_ascii=False)

    if settings:
        # 更新
        if settings_data.dingtalk_webhook is not None:
            settings.dingtalk_webhook = settings_data.dingtalk_webhook
        if settings_data.dingtalk_secret is not None:
            settings.dingtalk_secret = settings_data.dingtalk_secret
        if settings_data.llm_provider is not None:
            settings.llm_provider = settings_data.llm_provider
        if settings_data.llm_api_key is not None:
            settings.llm_api_key_encrypted = encrypt_api_key(settings_data.llm_api_key)
        if settings_data.llm_model is not None:
            settings.llm_model = settings_data.llm_model
        if settings_data.llm_group_id is not None:
            settings.llm_group_id = settings_data.llm_group_id
        if settings_data.rules is not None:
            settings.rules = rules_json
        if settings_data.enabled is not None:
            settings.enabled = settings_data.enabled
        if settings_data.daily_limit is not None:
            settings.daily_limit = settings_data.daily_limit
    else:
        # 创建
        settings = UserNotificationSettings(
            user_id=current_user.id,
            dingtalk_webhook=settings_data.dingtalk_webhook,
            dingtalk_secret=settings_data.dingtalk_secret,
            llm_provider=settings_data.llm_provider or "minmax",
            llm_api_key_encrypted=encrypt_api_key(settings_data.llm_api_key) if settings_data.llm_api_key else None,
            llm_model=settings_data.llm_model,
            llm_group_id=settings_data.llm_group_id,
            rules=rules_json,
            enabled=settings_data.enabled,
            daily_limit=settings_data.daily_limit
        )
        db.add(settings)

    await db.commit()

    return MessageResponse(message="设置保存成功")


@router.get("/logs", response_model=MessageResponse)
async def get_notification_logs(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知发送记录"""
    # 获取今日发送数量
    from datetime import datetime, timedelta, timezone
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(NotificationLog).where(
            NotificationLog.user_id == current_user.id,
            NotificationLog.sent_at >= today_start
        )
    )
    today_logs = result.scalars().all()

    # 获取历史记录
    offset = (page - 1) * page_size
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == current_user.id)
        .order_by(NotificationLog.sent_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return MessageResponse(data={
        "today_count": len(today_logs),
        "logs": [
            {
                "id": log.id,
                "task_id": log.task_id,
                "message_content": log.message_content,
                "is_read": log.is_read,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "read_at": log.read_at.isoformat() if log.read_at else None
            }
            for log in logs
        ]
    })


@router.post("/callback/{log_id}", response_model=MessageResponse)
async def notification_callback(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """已读回执回调 - 用户点击钉钉消息链接后调用"""
    from datetime import datetime, timezone

    result = await db.execute(
        select(NotificationLog).where(
            NotificationLog.id == log_id,
            NotificationLog.user_id == current_user.id
        )
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="通知记录不存在")

    log.is_read = True
    log.read_at = datetime.now(timezone.utc)
    await db.commit()

    return MessageResponse(message="已标记已读")


@router.get("/rules/template", response_model=MessageResponse)
async def get_rules_template():
    """获取规则模板"""
    return MessageResponse(data=DEFAULT_RULES)


@router.post("/trigger", response_model=MessageResponse)
async def trigger_reminder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动触发立即提醒（不计入每日配额）"""
    from app.services.reminder_scheduler import reminder_scheduler

    # 获取用户设置
    result = await db.execute(
        select(UserNotificationSettings).where(
            UserNotificationSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings or not settings.dingtalk_webhook:
        return MessageResponse(code=400, message="未配置钉钉Webhook")

    # 立即执行提醒检查（手动触发，不计入配额）
    result = await reminder_scheduler.check_user_notifications(settings, db, is_manual=True)

    if result is False:
        return MessageResponse(code=400, message="已达每日上限")
    elif result is True:
        return MessageResponse(message="提醒已发送")
    else:
        return MessageResponse(message="无需提醒")


@router.get("/stats", response_model=MessageResponse)
async def get_notification_stats(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知统计报表"""
    from datetime import timedelta

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # 获取该时间段内的通知
    result = await db.execute(
        select(NotificationLog).where(
            NotificationLog.user_id == current_user.id,
            NotificationLog.sent_at >= start_date
        )
    )
    logs = result.scalars().all()

    # 统计
    total = len(logs)
    auto_count = sum(1 for log in logs if not log.is_manual)
    manual_count = sum(1 for log in logs if log.is_manual)
    read_count = sum(1 for log in logs if log.is_read)
    read_rate = read_count / total * 100 if total > 0 else 0

    # 按日期统计（区分手动/自动）
    daily_stats = {}
    for log in logs:
        date_key = log.sent_at.strftime("%Y-%m-%d") if log.sent_at else "unknown"
        if date_key not in daily_stats:
            daily_stats[date_key] = {"auto": 0, "manual": 0}
        if log.is_manual:
            daily_stats[date_key]["manual"] += 1
        else:
            daily_stats[date_key]["auto"] += 1

    return MessageResponse(data={
        "total": total,
        "auto_count": auto_count,
        "manual_count": manual_count,
        "read_count": read_count,
        "read_rate": round(read_rate, 1),
        "daily_stats": daily_stats,
        "period_days": days
    })


@router.post("/intent/parse", response_model=MessageResponse)
async def parse_user_intent(
    text: str,
    current_user: User = Depends(get_current_user)
):
    """解析用户自然语言输入的意图"""
    from app.services.llm_service import LLMService

    llm = LLMService()
    result = await llm.parse_user_intent(text)

    return MessageResponse(data=result)


@router.post("/tasks/auto-classify", response_model=MessageResponse)
async def auto_classify_tasks(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """自动分类项目任务"""
    from app.services.llm_service import LLMService
    from app.models import Task

    # 获取项目任务
    result = await db.execute(
        select(Task).where(Task.project_id == project_id)
    )
    tasks = result.scalars().all()

    if not tasks:
        return MessageResponse(code=400, message="暂无任务")

    task_list = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "status": t.status,
            "progress": t.progress,
            "due_date": t.due_date.isoformat() if t.due_date else None
        }
        for t in tasks
    ]

    llm = LLMService()
    result = await llm.auto_classify_tasks(task_list)

    return MessageResponse(data=result)


# 依赖导入
from datetime import datetime, timedelta, timezone