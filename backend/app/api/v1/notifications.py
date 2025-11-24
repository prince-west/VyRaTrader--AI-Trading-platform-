from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import func, desc
from backend.app.db.session import get_session
from backend.app.db.models import Notification, User
from backend.app.core.security import get_current_user

router = APIRouter(tags=["notifications"])

@router.get("/notifications")
async def get_notifications(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    result = await session.execute(
        select(Notification).where(Notification.user_id == current_user.id).order_by(desc(Notification.created_at))
    )
    notifications = result.scalars().all()
    return notifications

@router.get("/count")
async def notifications_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.read == False
        )
    )
    count = result.scalar() or 0
    return {"unread_count": count}
