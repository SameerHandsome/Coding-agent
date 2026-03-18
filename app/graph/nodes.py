# app/graph/nodes.py
import json, logging
from langsmith import traceable
from langgraph.types import interrupt
from app.graph.state import AgentState
from app.db.postgres import AsyncSessionLocal
from app.db.redis import check_rate_limit
from app.memory.loader import MemoryLoader
from app.memory.saver import MemorySaver
from app.memory.context_builder import context_builder
from app.rag.hybrid_search import hybrid_searcher
from app.rag.indexer import code_indexer
from app.agents.orchestrator import orchestrator_chain
from app.agents.planner import planner_chain
from app.agents.architect import architect_chain
from app.agents.coder import coder_chain
from app.agents.reflexion import reflexion_chain
from app.tools.sandbox import sandbox_tool
from app.tools.github_tool import github_tool
from app.tools.web_search import web_search_tool
from app.api.middleware.output_filter import validate_llm_output

logger = logging.getLogger(__name__)


def _parse_llm_json(raw: str) -> dict:
    """
    Parse JSON from LLM response safely.
    Handles markdown fences, truncated responses, triple quotes.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned empty response")

    text = raw.strip()

    # Remove markdown code fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    # Replace triple quotes
    text = text.replace('"""', '\\"\\"\\"')

    # Find JSON start
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found: {text[:200]}")

    text = text[start:]

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to fix truncated JSON by finding last complete item
    # Strategy: find the last valid closing brace we can use
    for end in range(len(text), 0, -1):
        candidate = text[:end]
        # Try adding various closing sequences
        for suffix in ["", "}", "]}", '"}]}', '"]}', '"}]}'  ]:
            try:
                return json.loads(candidate + suffix)
            except json.JSONDecodeError:
                continue

    # Last resort — return empty files list so pipeline continues
    logger.warning(f"Could not parse JSON, returning empty result. Raw: {text[:200]}")
    return {"files": [], "task_graph": [], "chosen_stack": {}, 
            "reasoning": "", "alternatives_considered": [],
            "tasks_for_planner": [], "folder_structure": {},
            "file_responsibilities": {}, "design_decisions": []}

# ─── NODE 1: rate_limit_guard ────────────────────────────────────────────
async def rate_limit_guard_node(state: AgentState) -> dict:
    allowed = check_rate_limit(state["user_id"], state["user_tier"])
    if not allowed:
        return {"error_state": True, "error_detail": "rate_limit_exceeded"}
    return {"error_state": False, "current_node": "rate_limit_guard"}


# ─── NODE 2: memory_load ─────────────────────────────────────────────────
async def memory_load_node(state: AgentState) -> dict:
    async with AsyncSessionLocal() as db:
        loader = MemoryLoader(db)
        profile = await loader.load_user_profile(state["user_id"])
        history = await loader.load_chat_history(state["session_id"], limit=10)
        past_hitl = await loader.load_hitl_decisions(state["session_id"])
        rag = await hybrid_searcher.search(state["prd_content"], top_k=5)
        trimmed = context_builder.check_token_budget(
            {
                "user_profile": profile,
                "chat_history": history,
                "rag_context": rag,
                "past_hitl": past_hitl,
            }
        )
        return {
            "user_profile": trimmed["user_profile"],
            "chat_history": trimmed["chat_history"],
            "rag_context": trimmed["rag_context"],
            "past_hitl_decisions": trimmed["past_hitl"],
            "current_node": "memory_load",
        }


# ─── NODE 3: orchestrator ────────────────────────────────────────────────
@traceable(name="orchestrator --- LATS stack selection", run_type="chain")
async def orchestrator_node(state: AgentState) -> dict:
    web_context = await web_search_tool.search_for_stack_docs(state["prd_content"][:200])
    raw = await orchestrator_chain.ainvoke(
        {
            "user_name": state["user_profile"].get("name", "User"),
            "user_tier": state["user_tier"],
            "preferred_stack": state["user_profile"].get("preferred_stack", "none"),
            "rag_context": context_builder.format_rag_for_prompt(state["rag_context"]),
            "web_context": web_context,
            "past_hitl_decisions": context_builder.format_hitl_for_prompt(
                state["past_hitl_decisions"]
            ),
            "chat_history": state["chat_history"],
            "prd_content": state["prd_content"],
            "hitl_feedback": state.get("hitl_feedback", ""),
        }
    )
    validated = await validate_llm_output(raw)
    parsed = _parse_llm_json(validated)
    return {
    "chosen_stack": parsed.get("chosen_stack", {}),
    "stack_reasoning": parsed.get("reasoning", ""),
    "lats_alternatives": parsed.get("alternatives_considered", []),
    "current_node": "orchestrator",
    }


# ─── NODE 4: planner ─────────────────────────────────────────────────────
@traceable(name="planner --- task graph generation", run_type="chain")
async def planner_node(state: AgentState) -> dict:
    raw = await planner_chain.ainvoke(
        {
            "chat_history": state["chat_history"],
            "stack_json": json.dumps(state["chosen_stack"]),
            "tasks_list": "\n".join(
                state["chosen_stack"].get("tasks_for_planner", [])
            ),
            "prd_content": state["prd_content"],
        }
    )
    validated = await validate_llm_output(raw)
    parsed = _parse_llm_json(validated)
    return {"task_graph": parsed.get("task_graph", []), "current_node": "planner"}


# ─── NODE 5: hitl_1 --- stack approval ───────────────────────────────────
async def hitl_1_node(state: AgentState) -> dict:
    decision = interrupt(
        {
            "checkpoint": "stack_approval",
            "chosen_stack": state["chosen_stack"],
            "reasoning": state["stack_reasoning"],
            "alternatives": state["lats_alternatives"],
            "task_plan": state["task_graph"],
            "message": "Please review and approve the tech stack selection.",
        }
    )
    return {
        "hitl_1_approved": decision.get("approved", False),
        "hitl_feedback": decision.get("feedback", ""),
        "current_node": "hitl_1",
    }


# ─── NODE 6: architect ───────────────────────────────────────────────────
@traceable(name="architect --- folder structure design", run_type="chain")
async def architect_node(state: AgentState) -> dict:
    stack_name = state["chosen_stack"].get("name", "")
    arch_rag = await hybrid_searcher.search(f"folder structure {stack_name}", top_k=5)
    web_context = await web_search_tool.search_for_stack_docs(stack_name)
    raw = await architect_chain.ainvoke(
        {
            "chat_history": state["chat_history"],
            "stack_json": json.dumps(state["chosen_stack"]),
            "task_plan_json": json.dumps(state["task_graph"]),
            "rag_context": context_builder.format_rag_for_prompt(arch_rag),
            "web_context": web_context,
            "hitl_feedback": state.get("hitl_feedback", ""),
        }
    )
    validated = await validate_llm_output(raw)
    parsed = _parse_llm_json(validated)
    return {
    "folder_structure": parsed.get("folder_structure", {}),
    "file_responsibilities": parsed.get("file_responsibilities", {}),
    "design_decisions": parsed.get("design_decisions", []),
    "current_node": "architect",
    }


# ─── NODE 7: hitl_2 --- architecture approval ────────────────────────────
async def hitl_2_node(state: AgentState) -> dict:
    decision = interrupt(
        {
            "checkpoint": "architecture_approval",
            "folder_structure": state["folder_structure"],
            "file_responsibilities": state["file_responsibilities"],
            "design_decisions": state["design_decisions"],
            "message": "Please review the proposed folder structure and architecture.",
        }
    )
    return {
        "hitl_2_approved": decision.get("approved", False),
        "hitl_feedback": decision.get("feedback", ""),
        "current_node": "hitl_2",
    }


# ─── NODE 8: frontend_coder ──────────────────────────────────────────────
@traceable(name="coder --- frontend file generation", run_type="chain")
async def frontend_coder_node(state: AgentState) -> dict:
    tasks = [t for t in state["task_graph"] if t["assignee"] == "frontend_coder"]
    fe_rag = await hybrid_searcher.search(
        f"{state['chosen_stack'].get('frontend', '')} component patterns", top_k=5
    )
    rag_text = context_builder.format_rag_for_prompt(fe_rag)
    files = []
    for task in tasks:
        raw = await coder_chain.ainvoke(
            {
                "coder_role": "Frontend",
                "chat_history": state["chat_history"],
                "task_json": json.dumps(task),
                "stack_json": json.dumps(state["chosen_stack"]),
                "folder_structure": json.dumps(state["folder_structure"]),
                "file_responsibilities": json.dumps(state["file_responsibilities"]),
                "rag_context": rag_text,
                "existing_files_summary": str([f["path"] for f in files]),
            }
        )
        validated = await validate_llm_output(raw)
        files.extend(_parse_llm_json(validated).get("files", []))
    return {"frontend_files": files, "current_node": "frontend_coder"}


# ─── NODE 9: backend_coder ───────────────────────────────────────────────
@traceable(name="coder --- backend file generation", run_type="chain")
async def backend_coder_node(state: AgentState) -> dict:
    tasks = [t for t in state["task_graph"] if t["assignee"] == "backend_coder"]
    be_rag = await hybrid_searcher.search(
        f"{state['chosen_stack'].get('backend', '')} API patterns", top_k=5
    )
    rag_text = context_builder.format_rag_for_prompt(be_rag)
    files = []
    existing = [f["path"] for f in state.get("frontend_files", []) + files]
    for task in tasks:
        raw = await coder_chain.ainvoke(
            {
                "coder_role": "Backend",
                "chat_history": state["chat_history"],
                "task_json": json.dumps(task),
                "stack_json": json.dumps(state["chosen_stack"]),
                "folder_structure": json.dumps(state["folder_structure"]),
                "file_responsibilities": json.dumps(state["file_responsibilities"]),
                "rag_context": rag_text,
                "existing_files_summary": str(existing),
            }
        )
        validated = await validate_llm_output(raw)
        files.extend(_parse_llm_json(validated).get("files", []))
    return {"backend_files": files, "current_node": "backend_coder"}


# ─── NODE 10: db_coder ───────────────────────────────────────────────────
@traceable(name="coder --- database file generation", run_type="chain")
async def db_coder_node(state: AgentState) -> dict:
    tasks = [t for t in state["task_graph"] if t["assignee"] == "db_coder"]
    db_rag = await hybrid_searcher.search(
        f"SQLAlchemy {state['chosen_stack'].get('database', '')} models", top_k=5
    )
    rag_text = context_builder.format_rag_for_prompt(db_rag)
    files = []
    for task in tasks:
        raw = await coder_chain.ainvoke(
            {
                "coder_role": "Database",
                "chat_history": state["chat_history"],
                "task_json": json.dumps(task),
                "stack_json": json.dumps(state["chosen_stack"]),
                "folder_structure": json.dumps(state["folder_structure"]),
                "file_responsibilities": json.dumps(state["file_responsibilities"]),
                "rag_context": rag_text,
                "existing_files_summary": "[]",
            }
        )
        validated = await validate_llm_output(raw)
        files.extend(_parse_llm_json(validated).get("files", []))
    return {"db_files": files, "current_node": "db_coder"}


# ─── NODE 11: merge_code ─────────────────────────────────────────────────
async def merge_code_node(state: AgentState) -> dict:
    seen, merged = set(), []
    for f in (
        state.get("db_files", [])
        + state.get("backend_files", [])
        + state.get("frontend_files", [])
    ):
        if f["path"] not in seen:
            seen.add(f["path"])
            merged.append(f)
    return {"all_files": merged, "current_node": "merge_code"}


# ─── NODE 12: linter ─────────────────────────────────────────────────────
async def linter_node(state: AgentState) -> dict:
    result = await sandbox_tool.run_linter(state["all_files"])
    return {"lint_report": result, "current_node": "linter"}


# ─── NODE 13: tester ─────────────────────────────────────────────────────
async def tester_node(state: AgentState) -> dict:
    result = await sandbox_tool.run_tests(state["all_files"])
    return {
        "test_results": result,
        "tests_passed": result["success"],
        "error_message": result["output"] if not result["success"] else "",
        "current_node": "tester",
    }


# ─── NODE 14: reflexion ──────────────────────────────────────────────────
@traceable(name="reflexion --- root cause + fix", run_type="chain")
async def reflexion_node(state: AgentState) -> dict:
    new_retry = state.get("retry_count", 0) + 1
    err_rag = await hybrid_searcher.search(state["error_message"], top_k=3)
    rag_text = context_builder.format_rag_for_prompt(err_rag)
    raw = await reflexion_chain.ainvoke(
        {
            "retry_count": new_retry,
            "chat_history": [],
            "failed_files_summary": str([f["path"] for f in state["all_files"]]),
            "error_message": state["error_message"],
            "test_output": state["test_results"].get("output", ""),
            "lint_output": state["lint_report"].get("output", ""),
            "rag_context": rag_text,
        }
    )
    validated = await validate_llm_output(raw)
    parsed = _parse_llm_json(validated)

    fixed_map = {f["path"]: f["content"] for f in parsed.get("files_to_change", [])}
    new_files = [
        {"path": f["path"], "content": fixed_map.get(f["path"], f["content"])}
        for f in state["all_files"]
    ]
    existing = {f["path"] for f in state["all_files"]}
    for f in parsed.get("files_to_change", []):
        if f["path"] not in existing:
            new_files.append(f)

    await code_indexer.index_error_fix_pair(
        error=state["error_message"],
        fix=parsed.get("fix_instruction", ""),
        stack=state["chosen_stack"].get("name", ""),
    )
    return {
        "retry_count": new_retry,
        "reflexion_output": parsed,
        "all_files": new_files,
        "current_node": "reflexion",
    }


# ─── NODE 15: hitl_3 --- code review ─────────────────────────────────────
async def hitl_3_node(state: AgentState) -> dict:
    decision = interrupt(
        {
            "checkpoint": "code_review",
            "files": state["all_files"],
            "test_results": state["test_results"],
            "lint_report": state["lint_report"],
            "message": "Please review the generated codebase and test results.",
        }
    )
    return {
        "hitl_3_approved": decision.get("approved", False),
        "hitl_feedback": decision.get("feedback", ""),
        "current_node": "hitl_3",
    }


# ─── NODE 16: hitl_4 --- github push approval ────────────────────────────
async def hitl_4_node(state: AgentState) -> dict:
    decision = interrupt(
        {
            "checkpoint": "github_push_approval",
            "project_name": state["project_name"],
            "files_count": len(state["all_files"]),
            "message": "Approve push to GitHub and PR creation?",
        }
    )
    return {
        "hitl_4_approved": decision.get("approved", False),
        "hitl_feedback": decision.get("feedback", ""),
        "current_node": "hitl_4",
    }


# ─── NODE 17: github_push ────────────────────────────────────────────────
async def github_push_node(state: AgentState) -> dict:
    branch = "feature/initial-build"
    repo_name = await github_tool.create_repo(state["project_name"])
    commit_sha = await github_tool.push_files(
        repo_full_name=repo_name,
        branch=branch,
        files=state["all_files"],
        commit_message="feat: initial build by App Builder Agent",
    )
    pr_url = await github_tool.open_pull_request(
        repo_full_name=repo_name,
        title=f"Initial Build: {state['project_name']}",
        head=branch,
        base="main",
    )
    return {
        "github_repo_name": repo_name,
        "github_pr_url": pr_url,
        "current_node": "github_push",
    }


# ─── NODE 18: memory_save ────────────────────────────────────────────────
async def memory_save_node(state: AgentState) -> dict:
    async with AsyncSessionLocal() as db:
        saver = MemorySaver(db)
        await saver.save_message(
            session_id=state["session_id"],
            role="assistant",
            content=f"Build complete. PR: {state['github_pr_url']}",
            agent_name="github_push",
        )
        for cp, approved in [
            ("stack_approval", state.get("hitl_1_approved", False)),
            ("architecture_approval", state.get("hitl_2_approved", False)),
            ("code_review", state.get("hitl_3_approved", False)),
            ("github_push_approval", state.get("hitl_4_approved", False)),
        ]:
            await saver.save_hitl_decision(state["session_id"], cp, approved)

        await saver.upsert_code_patterns(
            state["all_files"],
            state["chosen_stack"].get("name", ""),
            state["session_id"],
        )
        await saver.mark_session_complete(state["session_id"], state["github_pr_url"])
    return {"current_node": "memory_save"}