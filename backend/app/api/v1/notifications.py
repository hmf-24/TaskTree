from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.models import User, Notification
from app.schemas import MessageResponse
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("", response_model=MessageResponse)
async def list_notifications(
    is_read: bool = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(Notification.user_id == current_user.id)

    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return MessageResponse(
        data={
            "items": [
                {
                    "id": n.id,
                    "user_id": n.user_id,
                    "type": n.type,
                    "title": n.title,
                    "content": n.content,
                    "related_id": n.related_id,
                    "related_type": n.related_type,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat(),
                }
                for n in notifications
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.put("/{notification_id}/read", response_model=MessageResponse)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == current_user.id)
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = True
    await db.commit()

    return MessageResponse(message="标记已读")


@router.put("/read-all", response_model=MessageResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            and_(Notification.user_id == current_user.id, Notification.is_read == False)
        )
    )
    notifications = result.scalars().all()

    for n in notifications:
        n.is_read = True

    await db.commit()

    return MessageResponse(message=f"已标记 {len(notifications)} 条通知为已读")
