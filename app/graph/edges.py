# app/graph/edges.py
from langgraph.types import Send
from app.graph.state import AgentState


def route_after_rate_limit(state: AgentState) -> str:
    return "__end__" if state.get("error_state") else "memory_load"


def route_after_hitl_1(state: AgentState) -> str:
    return "architect" if state.get("hitl_1_approved") else "orchestrator"


def route_after_hitl_2(state: AgentState):
    if state.get("hitl_2_approved"):
        # Fan-out to all 3 coders in parallel using Send()
        return [
            Send("frontend_coder", state),
            Send("backend_coder", state),
            Send("db_coder", state),
        ]
    return "architect"


def route_after_tests(state: AgentState) -> str:
    if state.get("tests_passed"):
        return "hitl_3"
    if state.get("retry_count", 0) >= 3:
        return "hitl_3"
    return "reflexion"


def route_after_reflexion(state: AgentState) -> str:
    return "linter"


def route_after_hitl_3(state: AgentState) -> str:
    return "hitl_4" if state.get("hitl_3_approved") else "backend_coder"


def route_after_hitl_4(state: AgentState) -> str:
    return "github_push" if state.get("hitl_4_approved") else "hitl_3"