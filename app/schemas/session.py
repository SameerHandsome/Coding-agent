# app/schemas/session.py
from pydantic import BaseModel, field_validator
from uuid import UUID
from typing import Optional, Any, Dict


class SessionStartRequest(BaseModel):
    prd_content: str
    project_name: str

    @field_validator("prd_content")
    @classmethod
    def prd_length(cls, v):
        if len(v) < 20:
            raise ValueError("PRD too short")
        if len(v) > 10000:
            raise ValueError("PRD too long")
        return v

    @field_validator("project_name")
    @classmethod
    def slugify(cls, v):
        return v.strip().lower().replace(" ", "-")


class CheckpointInfo(BaseModel):
    checkpoint: str
    payload: Dict[str, Any]
    message: str


class SessionStartResponse(BaseModel):
    session_id: UUID
    status: str
    checkpoint_info: Optional[CheckpointInfo] = None


class SessionStateResponse(BaseModel):
    session_id: UUID
    current_node: str
    status: str
    checkpoint: Optional[str] = None
    pr_url: Optional[str] = None
    error_detail: Optional[str] = None
