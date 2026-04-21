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
    credentials: str = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """从 auth 路由导入 get_current_user 函数"""
    from app.api.v1.auth import get_current_user as _get_current_user
    from fastapi.security import HTTPAuthorizationCredentials
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)
    return await _get_current_user(creds, db)


# 默认提醒规则模板
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
            minmax_api_key=None,
            minmax_group_id=None,
            rules=DEFAULT_RULES,
            enabled=True,
            daily_limit=5
        )

    # 解析 rules JSON
    rules = json.loads(settings.rules) if settings.rules else DEFAULT_RULES

    return UserNotificationSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        dingtalk_webhook=settings.dingtalk_webhook,
        dingtalk_secret=settings.dingtalk_secret,
        minmax_api_key=settings.minmax_api_key,
        minmax_group_id=settings.minmax_group_id,
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
        if settings_data.minmax_api_key is not None:
            settings.minmax_api_key = settings_data.minmax_api_key
        if settings_data.minmax_group_id is not None:
            settings.minmax_group_id = settings_data.minmax_group_id
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
            minmax_api_key=settings_data.minmax_api_key,
            minmax_group_id=settings_data.minmax_group_id,
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