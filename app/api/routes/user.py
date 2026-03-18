# app/api/routes/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres import get_db
from app.db.models import User, Session as SessionModel
from app.core.security import get_current_user
from app.schemas.user import UserHistoryResponse, UserResponse, SessionSummary

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=UserHistoryResponse)
async def profile(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    r = await db.execute(select(User).where(User.id == user["user_id"]))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    sr = await db.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user["user_id"])
        .order_by(SessionModel.created_at.desc())
    )
    return UserHistoryResponse(
        user=UserResponse.model_validate(u),
        sessions=[SessionSummary.model_validate(s) for s in sr.scalars().all()],
    )
