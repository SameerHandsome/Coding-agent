# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from typing import Optional, List


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    tier: str
    preferred_stack: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    id: UUID
    project_name: str
    status: str
    pr_url: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UserHistoryResponse(BaseModel):
    user: UserResponse
    sessions: List[SessionSummary]
