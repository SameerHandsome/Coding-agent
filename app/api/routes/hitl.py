# app/api/routes/hitl.py
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.security import get_current_user
from app.schemas.hitl import HitlApprovalRequest, HitlApprovalResponse, HitlPendingResponse
from app.graph.builder import get_checkpointer
from langgraph.types import Command

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.post("/{session_id}/approve", response_model=HitlApprovalResponse)
async def approve(
    session_id: str,
    body: HitlApprovalRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    # Ensure checkpointer is alive
    await get_checkpointer()

    graph = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}

    # Resume the interrupted graph with the user's decision
    await graph.ainvoke(
        Command(resume={"approved": body.approved, "feedback": body.feedback or ""}),
        config=config,
    )

    gs = await graph.aget_state(config)
    vals = gs.values if gs else {}
    next_cp = None
    if gs and gs.next and gs.tasks and gs.tasks[0].interrupts:
        next_cp = gs.tasks[0].interrupts[0].value.get("checkpoint")

    return HitlApprovalResponse(
        session_id=session_id,
        status="awaiting_next" if next_cp else "completed",
        next_checkpoint=next_cp,
        pr_url=vals.get("github_pr_url"),
    )


@router.get("/{session_id}/pending", response_model=HitlPendingResponse)
async def get_pending(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    # Ensure checkpointer is alive
    await get_checkpointer()

    graph = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    gs = await graph.aget_state(config)
    if not gs or not gs.tasks or not gs.tasks[0].interrupts:
        raise HTTPException(404, "No pending checkpoint")
    payload = gs.tasks[0].interrupts[0].value
    return HitlPendingResponse(
        session_id=session_id,
        checkpoint_name=payload.get("checkpoint", ""),
        payload=payload,
        message=payload.get("message", ""),
    )