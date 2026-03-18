# app/memory/loader.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import User, Session, MessageHistory, HitlDecision
from typing import List, Dict


class MemoryLoader:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_user_profile(self, user_id: str) -> Dict:
        r = await self.db.execute(select(User).where(User.id == user_id))
        u = r.scalar_one_or_none()
        if not u:
            return {}
        return {
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "tier": u.tier,
            "preferred_stack": u.preferred_stack or "none",
        }

    async def load_chat_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        r = await self.db.execute(
            select(MessageHistory)
            .where(MessageHistory.session_id == session_id)
            .order_by(desc(MessageHistory.timestamp))
            .limit(limit)
        )
        return [{"role": m.role, "content": m.content} for m in reversed(r.scalars().all())]

    async def load_hitl_decisions(self, session_id: str) -> List[Dict]:
        r = await self.db.execute(
            select(HitlDecision)
            .where(HitlDecision.session_id == session_id)
            .order_by(HitlDecision.timestamp)
        )
        return [
            {
                "checkpoint": d.checkpoint_name,
                "approved": d.user_decision,
                "feedback": d.user_feedback or "",
            }
            for d in r.scalars().all()
        ]
