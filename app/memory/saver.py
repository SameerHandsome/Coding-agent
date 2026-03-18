# app/memory/saver.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.db.models import MessageHistory, HitlDecision, ReflexionLog, Session
from app.rag.indexer import code_indexer
from datetime import datetime, timezone
from typing import List, Dict, Optional


class MemorySaver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_message(
        self,
        session_id,
        role,
        content,
        agent_name=None,
        token_count=None,
    ):
        self.db.add(
            MessageHistory(
                session_id=session_id,
                role=role,
                content=content,
                agent_name=agent_name,
                token_count=token_count,
            )
        )
        await self.db.commit()

    async def save_hitl_decision(
        self, session_id, checkpoint_name, decision, feedback=None
    ):
        self.db.add(
            HitlDecision(
                session_id=session_id,
                checkpoint_name=checkpoint_name,
                user_decision=decision,
                user_feedback=feedback,
            )
        )
        await self.db.commit()

    async def save_reflexion_log(
        self,
        session_id,
        retry_number,
        error_type,
        error_message,
        fix_applied,
        was_successful,
    ):
        self.db.add(
            ReflexionLog(
                session_id=session_id,
                retry_number=retry_number,
                error_type=error_type,
                error_message=error_message,
                fix_applied=fix_applied,
                was_successful=was_successful,
            )
        )
        await self.db.commit()

    async def upsert_code_patterns(self, files, stack, session_id):
        await code_indexer.index_code_files(files, stack, session_id)

    async def mark_session_complete(self, session_id, pr_url):
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(
                status="completed",
                pr_url=pr_url,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
