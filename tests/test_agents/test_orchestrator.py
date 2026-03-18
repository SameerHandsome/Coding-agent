# tests/test_agents/test_orchestrator.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.graph.nodes import orchestrator_node

VALID = json.dumps(
    {
        "chosen_stack": {
            "name": "React+FastAPI",
            "frontend": "React",
            "backend": "FastAPI",
            "database": "PostgreSQL",
            "extra": [],
        },
        "reasoning": "Best fit",
        "alternatives_considered": [
            {"stack": "Vue", "score": 70, "rejected_because": "less popular"},
            {"stack": "Angular", "score": 60, "rejected_because": "too heavy"},
        ],
        "tasks_for_planner": ["Build auth", "Build API"],
    }
)


def base_state():
    return {
        "user_id": "u1",
        "session_id": "s1",
        "user_tier": "free",
        "prd_content": "Build a todo app with auth and task CRUD.",
        "project_name": "todo",
        "user_profile": {"name": "Test", "tier": "free", "preferred_stack": "none"},
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


@pytest.mark.asyncio
async def test_orchestrator_returns_valid_stack():
    state = base_state()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=VALID)

    with patch("app.graph.nodes.orchestrator_chain", mock_chain), \
         patch("app.graph.nodes.validate_llm_output", new=AsyncMock(return_value=VALID)), \
         patch("app.graph.nodes.web_search_tool.search_for_stack_docs", new=AsyncMock(return_value="no results")), \
         patch("app.graph.nodes.hybrid_searcher.search", new=AsyncMock(return_value=[])):
        result = await orchestrator_node(state)
        assert result["chosen_stack"]["frontend"] == "React"
        assert len(result["lats_alternatives"]) == 2


@pytest.mark.asyncio
async def test_orchestrator_handles_groq_timeout():
    state = base_state()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(side_effect=Exception("Groq timeout"))

    with patch("app.graph.nodes.orchestrator_chain", mock_chain), \
         patch("app.graph.nodes.web_search_tool.search_for_stack_docs", new=AsyncMock(return_value="")), \
         patch("app.graph.nodes.hybrid_searcher.search", new=AsyncMock(return_value=[])):
        with pytest.raises(Exception, match="Groq timeout"):
            await orchestrator_node(state)


@pytest.mark.asyncio
async def test_orchestrator_lats_generates_3_total():
    state = base_state()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=VALID)

    with patch("app.graph.nodes.orchestrator_chain", mock_chain), \
         patch("app.graph.nodes.validate_llm_output", new=AsyncMock(return_value=VALID)), \
         patch("app.graph.nodes.web_search_tool.search_for_stack_docs", new=AsyncMock(return_value="")), \
         patch("app.graph.nodes.hybrid_searcher.search", new=AsyncMock(return_value=[])):
        result = await orchestrator_node(state)
        assert len(result["lats_alternatives"]) == 2
        assert result["chosen_stack"]["name"] == "React+FastAPI"


@pytest.mark.asyncio
async def test_tavily_failure_is_graceful():
    """Tavily failing should not stop the orchestrator."""
    state = base_state()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=VALID)

    with patch("app.graph.nodes.orchestrator_chain", mock_chain), \
         patch("app.graph.nodes.validate_llm_output", new=AsyncMock(return_value=VALID)), \
         patch("app.graph.nodes.web_search_tool.search_for_stack_docs", new=AsyncMock(return_value="No web results.")), \
         patch("app.graph.nodes.hybrid_searcher.search", new=AsyncMock(return_value=[])):
        result = await orchestrator_node(state)
        assert "chosen_stack" in result