# app/schemas/hitl.py
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any, Dict


class HitlApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


class HitlPendingResponse(BaseModel):
    session_id: UUID
    checkpoint_name: str
    payload: Dict[str, Any]
    message: str


class HitlApprovalResponse(BaseModel):
    session_id: UUID
    status: str
    next_checkpoint: Optional[str] = None
    pr_url: Optional[str] = None