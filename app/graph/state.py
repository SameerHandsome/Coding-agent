# app/graph/state.py
from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph.message import add_messages
import operator


def _last_value(a, b):
    """For fields written by parallel nodes — keep the last value."""
    return b


def _extend_list(a, b):
    """For file lists written by parallel nodes — merge them."""
    if a is None:
        a = []
    if b is None:
        b = []
    return a + b


class AgentState(TypedDict):
    # Identity
    user_id: str
    session_id: str
    user_tier: str

    # Input
    prd_content: str
    project_name: str

    # Memory
    user_profile: Dict
    chat_history: List[Dict]
    rag_context: List[Dict]
    past_hitl_decisions: List[Dict]

    # Orchestrator
    chosen_stack: Dict
    stack_reasoning: str
    lats_alternatives: List[Dict]

    # Planner
    task_graph: List[Dict]

    # HITL gates
    hitl_1_approved: bool
    hitl_2_approved: bool
    hitl_3_approved: bool
    hitl_4_approved: bool
    hitl_feedback: str

    # Architect
    folder_structure: Dict
    file_responsibilities: Dict
    design_decisions: List[str]

    # Coders — use extend reducer for parallel writes
    frontend_files: Annotated[List[Dict], _extend_list]
    backend_files: Annotated[List[Dict], _extend_list]
    db_files: Annotated[List[Dict], _extend_list]
    all_files: List[Dict]

    # Quality
    lint_report: Dict
    test_results: Dict
    tests_passed: bool

    # Reflexion
    retry_count: int
    reflexion_output: Dict
    error_message: str

    # GitHub
    github_repo_name: str
    github_pr_url: str

    # Routing — use last_value reducer for parallel writes
    current_node: Annotated[str, _last_value]
    error_state: bool
    error_detail: str