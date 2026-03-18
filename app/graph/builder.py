# app/graph/builder.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.graph.state import AgentState
from app.graph.nodes import (
    rate_limit_guard_node,
    memory_load_node,
    orchestrator_node,
    planner_node,
    hitl_1_node,
    architect_node,
    hitl_2_node,
    frontend_coder_node,
    backend_coder_node,
    db_coder_node,
    merge_code_node,
    linter_node,
    tester_node,
    reflexion_node,
    hitl_3_node,
    hitl_4_node,
    github_push_node,
    memory_save_node,
)
from app.graph.edges import (
    route_after_rate_limit,
    route_after_hitl_1,
    route_after_hitl_2,
    route_after_tests,
    route_after_reflexion,
    route_after_hitl_3,
    route_after_hitl_4,
)
from app.core.config import settings
from psycopg_pool import AsyncConnectionPool
import logging

logger = logging.getLogger(__name__)

_pool = None
_checkpointer = None


def _get_pg_url():
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


async def get_checkpointer():
    global _pool, _checkpointer

    # Always try to close and recreate if pool exists but connection is bad
    if _pool is not None:
        try:
            async with _pool.connection() as conn:
                await conn.execute("SELECT 1")
            # Pool is healthy, return existing checkpointer
            return _checkpointer
        except Exception as e:
            logger.warning(f"Pool connection failed: {e} — reconnecting...")
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None
            _checkpointer = None

    # Create fresh pool
    pg_url = _get_pg_url()
    _pool = AsyncConnectionPool(
        conninfo=pg_url,
        min_size=1,
        max_size=5,
        open=False,
        reconnect_timeout=30,
        kwargs={
            "autocommit": True,
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )
    await _pool.open(wait=True, timeout=30)
    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()
    logger.info("Checkpointer reconnected successfully")
    return _checkpointer


async def close_checkpointer():
    global _pool, _checkpointer
    if _pool and not _pool.closed:
        await _pool.close()
    _pool = None
    _checkpointer = None
    logger.info("Checkpointer pool closed")


async def build_graph():
    checkpointer = await get_checkpointer()

    g = StateGraph(AgentState)

    g.add_node("rate_limit_guard", rate_limit_guard_node)
    g.add_node("memory_load", memory_load_node)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("planner", planner_node)
    g.add_node("hitl_1", hitl_1_node)
    g.add_node("architect", architect_node)
    g.add_node("hitl_2", hitl_2_node)
    g.add_node("frontend_coder", frontend_coder_node)
    g.add_node("backend_coder", backend_coder_node)
    g.add_node("db_coder", db_coder_node)
    g.add_node("merge_code", merge_code_node)
    g.add_node("linter", linter_node)
    g.add_node("tester", tester_node)
    g.add_node("reflexion", reflexion_node)
    g.add_node("hitl_3", hitl_3_node)
    g.add_node("hitl_4", hitl_4_node)
    g.add_node("github_push", github_push_node)
    g.add_node("memory_save", memory_save_node)

    g.add_edge(START, "rate_limit_guard")
    g.add_conditional_edges(
        "rate_limit_guard",
        route_after_rate_limit,
        {"memory_load": "memory_load", "__end__": END},
    )
    g.add_edge("memory_load", "orchestrator")
    g.add_edge("orchestrator", "planner")
    g.add_edge("planner", "hitl_1")
    g.add_conditional_edges(
        "hitl_1",
        route_after_hitl_1,
        {"architect": "architect", "orchestrator": "orchestrator"},
    )
    g.add_edge("architect", "hitl_2")
    g.add_conditional_edges(
        "hitl_2",
        route_after_hitl_2,
        ["frontend_coder", "backend_coder", "db_coder", "architect"],
    )
    g.add_edge("frontend_coder", "merge_code")
    g.add_edge("backend_coder", "merge_code")
    g.add_edge("db_coder", "merge_code")
    g.add_edge("merge_code", "linter")
    g.add_edge("linter", "tester")
    g.add_conditional_edges(
        "tester",
        route_after_tests,
        {"hitl_3": "hitl_3", "reflexion": "reflexion"},
    )
    g.add_conditional_edges(
        "reflexion",
        route_after_reflexion,
        {"linter": "linter"},
    )
    g.add_conditional_edges(
        "hitl_3",
        route_after_hitl_3,
        {"hitl_4": "hitl_4", "backend_coder": "backend_coder"},
    )
    g.add_conditional_edges(
        "hitl_4",
        route_after_hitl_4,
        {"github_push": "github_push", "hitl_3": "hitl_3"},
    )
    g.add_edge("github_push", "memory_save")
    g.add_edge("memory_save", END)

    compiled = g.compile(checkpointer=checkpointer)
    logger.info("LangGraph compiled --- 18 nodes, 7 conditional edges")
    return compiled