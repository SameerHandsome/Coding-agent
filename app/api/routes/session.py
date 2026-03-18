# app/api/routes/session.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import get_db
from app.db.models import Session as SessionModel, MessageHistory
from app.core.security import get_current_user
from app.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionStateResponse,
    CheckpointInfo,
)
from app.graph.builder import get_checkpointer, build_graph as _build_graph
from app.api.middleware.input_filter import filter_input
from app.graph.state import AgentState
from app.graph.builder import get_checkpointer
import uuid

router = APIRouter(prefix="/session", tags=["session"])


def _empty_state(user_id, session_id, user_tier, prd_content, project_name) -> AgentState:
    return {
        "user_id": user_id,
        "session_id": session_id,
        "user_tier": user_tier,
        "prd_content": prd_content,
        "project_name": project_name,
        "user_profile": {},
        "chat_history": [],
        "rag_context": [],
        "past_hitl_decisions": [],
        "chosen_stack": {},
        "stack_reasoning": "",
        "lats_alternatives": [],
        "task_graph": [],
        "hitl_1_approved": False,
        "hitl_2_approved": False,
        "hitl_3_approved": False,
        "hitl_4_approved": False,
        "hitl_feedback": "",
        "folder_structure": {},
        "file_responsibilities": {},
        "design_decisions": [],
        "frontend_files": [],
        "backend_files": [],
        "db_files": [],
        "all_files": [],
        "lint_report": {},
        "test_results": {},
        "tests_passed": False,
        "retry_count": 0,
        "reflexion_output": {},
        "error_message": "",
        "github_repo_name": "",
        "github_pr_url": "",
        "current_node": "",
        "error_state": False,
        "error_detail": "",
    }


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    body: SessionStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    check = filter_input(body.prd_content)
    if not check["clean"]:
        raise HTTPException(400, check["reason"])

    session_id = str(uuid.uuid4())
    db.add(
        SessionModel(
            id=session_id,
            user_id=user["user_id"],
            project_name=body.project_name,
            prd_content=body.prd_content,
            status="active",
        )
    )
    db.add(
        MessageHistory(
            session_id=session_id, role="user", content=body.prd_content
        )
    )
    await db.commit()

    # Ensure checkpointer pool is alive before invoking graph
    # Reconnect checkpointer if needed and rebuild graph
    checkpointer = await get_checkpointer()
    if checkpointer is not request.app.state.graph.checkpointer:
       request.app.state.graph = await _build_graph()

    graph = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    await graph.ainvoke(
        _empty_state(
            user["user_id"],
            session_id,
            user["tier"],
            body.prd_content,
            body.project_name,
        ),
        config=config,
    )

    gs = await graph.aget_state(config)
    next_ = gs.next[0] if gs.next else None
    cpinfo = None
    if next_ and gs.tasks and gs.tasks[0].interrupts:
        iv = gs.tasks[0].interrupts[0].value
        cpinfo = CheckpointInfo(
            checkpoint=iv.get("checkpoint", ""),
            payload=iv,
            message=iv.get("message", ""),
        )

    return SessionStartResponse(
        session_id=session_id,
        status="awaiting_approval" if cpinfo else "running",
        checkpoint_info=cpinfo,
    )


@router.get("/{session_id}/state", response_model=SessionStateResponse)
async def get_state(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    # Ensure checkpointer pool is alive
    await get_checkpointer()

    graph = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    gs = await graph.aget_state(config)
    vals = gs.values if gs else {}
    return SessionStateResponse(
        session_id=session_id,
        current_node=vals.get("current_node", "unknown"),
        status="awaiting_approval" if gs and gs.next else "completed",
        checkpoint=gs.next[0] if gs and gs.next else None,
        pr_url=vals.get("github_pr_url"),
        error_detail=vals.get("error_detail"),
    )