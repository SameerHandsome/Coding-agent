## App Builder Agent (Coding-agent)

A local developer assistant / project-building agent framework that orchestrates several AI-driven components to help design, scaffold, and manage application projects. This repository implements a modular agent platform with components for agent orchestration, graph-based workflows, retrieval-augmented generation (RAG), memory, tools (GitHub, web search, sandbox), an HTTP API, and persistence (Postgres + Qdrant + Redis).

This README explains what the project does, how it is organized, and how each file/folder contributes to the overall system. It also includes instructions to run, test, and develop locally.

---

## Table of contents

- Project overview
- Architecture and data flow
- Files & folders (detailed)
- Configuration & environment variables
- Install & run (development)
- Running tests
- Database migrations
- Development notes and tips
- Contributing
- License

---

## Project overview

The App Builder Agent is an orchestration layer for AI workflows that helps generate, plan, and manage software projects. It coordinates multiple "agents" (architect, coder, planner, orchestrator, reflexion) to take a user-provided product requirement and produce structured outputs (project plans, code, sessions). The system exposes an HTTP API (FastAPI) for interactive usage and integrates with backing services for persistence, embedding search, and external tooling.

Key capabilities:
- Agent orchestration: multiple specialized agents coordinate to perform multi-step workflows.
- Graph-based workflow engine: uses a graph abstraction (langgraph) to model flows and steps; the graph is invoked with an initial state.
- Retrieval-augmented generation (RAG): hybrid search backed by vector store (Qdrant) + optional hybrid components.
- Persistence: Postgres (async SQLAlchemy/alembic) for structured data and checkpoints, Upstash Redis for lightweight state/locks.
- Tools: direct SDK integrations for GitHub, web search (Tavily), a code-sandbox (E2B), and others.

---

## Architecture & data flow (high level)

1. Client calls the API (or the programmatic `main()` function in `app/main.py`) with a product requirement and session/user metadata.
2. FastAPI lifecyle ensures database and graph are initialized (see `lifespan` in `app/main.py`).
3. The system builds (or loads) a graph from `app/graph/builder.py`. The graph encodes the steps and agents in the workflow.
4. The initial state is prepared (session state), and the graph is invoked asynchronously. The graph coordinates calls to agent modules, tools, and the RAG/search layer.
5. Agents and tools call external services or run local logic to produce artifacts. Intermediate state and checkpoints are stored in the DB or checkpointers.
6. Results are returned to the API caller and optionally persisted as a session.

---

## Files & folders (detailed)

Top-level files:
- `README.md` (this file)
- `requirements.txt` - pinned Python dependency list used by the project.
- `alembic.ini`, `migrations/` - database migration configuration and migration files for Postgres.
- `pytest.ini` - test runner configuration.

`app/` - main Python package. Key subpackages and files below.

- `app/main.py`
  - Bootstraps the FastAPI application.
  - Provides a `lifespan` async context manager used to initialize resources: `init_db()`, `build_graph()`, and the RAG collection.
  - Registers middleware (CORS, rate limiter) and routers for API endpoints.
  - Adds custom OpenAPI schema to present HTTP Bearer auth in Swagger.
  - Exposes a programmatic `main()` function decorated with `traceable` for direct SDK invocations of the graph with an initial state.

- `app/core/`
  - `config.py` — Pydantic settings object (`Settings`) which reads environment variables from `.env` (see `Settings` fields). It validates important config values (e.g., database URL, JWT secret length) and sets a few LANGCHAIN-related env vars.
  - `llm.py` — (not listed fully here) likely contains LLM client wiring and helper functions used by agents.
  - `security.py` — authentication/authorization helpers used by the API.

- `app/db/`
  - `postgres.py` — async DB initialization and helpers (SQLAlchemy async engine, session factory). Called during app startup/shutdown.
  - `models.py` — database models (ORM) used by the app.
  - `redis.py` — Upstash Redis helper/wrapper used for session locks, rate limiting, or ephemeral state.

- `app/graph/`
  - `builder.py` — builds or loads the `langgraph` graph and sets up checkpointers. This is central: the graph encodes the agent workflow.
  - `nodes.py`, `edges.py`, `state.py` — the building blocks for graph nodes, transitions, and the shape of state passed through the graph.
  - Graph checkpointer support likely uses Postgres-backed checkpoints (see package `langgraph-checkpoint-postgres`).

- `app/agents/`
  - `architect.py`, `coder.py`, `orchestrator.py`, `planner.py`, `reflexion.py` — specialized agent modules that implement different responsibilities in the pipeline. Each agent will typically accept structured input, call an LLM/tooling pipeline, and return structured outputs or state updates.

- `app/rag/`
  - `embedder.py` — embedding wrapper used to produce vector embeddings for documents/snippets.
  - `hybrid_search.py` — the hybrid search implementation that integrates vector search (Qdrant) and likely additional filters or heuristics. `hybrid_searcher.ensure_collection()` is called during startup to guarantee the vector collection exists.
  - `indexer.py` — indexing utilities to add documents to the vector store.

- `app/memory/`
  - `context_builder.py`, `loader.py`, `saver.py` — helpers to build a context window, persist and load memory, and save state between sessions.

- `app/prompts/`
  - `architect.py`, `coder.py`, `orchestrator.py`, `planner.py`, `reflexion.py` — central prompt templates and prompt composition helpers used by the agents.

- `app/api/`
  - `routes/` - API route modules split by domain: `auth.py`, `session.py`, `hitl.py`, `user.py`.
    - `auth.py` — endpoints to authenticate users and obtain JWTs.
    - `session.py` — endpoints to create, resume, and inspect sessions (session state is the main way users interact with agent runs).
    - `hitl.py` — human-in-the-loop endpoints for review/approval or intervention.
    - `user.py` — user management endpoints.
  - `middleware/` - middleware components:
    - `input_filter.py` / `output_filter.py` — sanitize or normalize requests/responses.
    - `rate_limiter.py` — request throttling and rate limiting (registered in `app/main.py`).

- `app/tools/`
  - `github_tool.py` — direct SDK integration with GitHub (PyGithub). Used to create repositories, push scaffolding, etc.
  - `web_search.py` — web-search integration (Tavily SDK) used for external context discovery.
  - `sandbox.py` — an E2B code sandbox tool for running or validating snippets.
  - `token_counter.py` — token counting utilities for LLM usage budgeting.

- `app/schemas/`
  - Pydantic models used for request/response validation across the API and internal RPC-style calls.

- `migrations/` & `alembic.ini`
  - Alembic migration scripts for the Postgres schema.

- `tests/` - unit and integration tests. Examples:
  - `tests/test_agents/test_orchestrator.py` — tests for orchestrator agent logic.
  - `tests/test_tools/test_github_tool.py`, `tests/test_tools/test_web_search.py` — tests for tool integrations.

---

## Configuration & environment variables

Configuration is handled by `app/core/config.py` which reads from environment variables and an optional `.env` file. Important settings include:

- `database_url` (required) — Postgres connection string. Must begin with `postgresql+asyncpg://`.
- `upstash_redis_url` and `upstash_redis_token` — Upstash Redis credentials.
- `qdrant_url`, `qdrant_api_key`, `qdrant_collection_name` — Qdrant vector store config.
- `langchain_api_key`, `langchain_project`, `langchain_tracing_v2` — LangChain / LangSmith integration keys and tracing toggles.
- `jwt_secret_key`, `jwt_algorithm`, `jwt_expire_minutes` — JWT auth settings (secret must be >= 32 chars).
- `github_token`, `github_default_org` — GitHub SDK token and default org.
- `e2b_api_key`, `tavily_api_key`, `guardrails_api_key` — external tool API keys.
- `app_env` — "development", "staging", or "production". Controls docs exposure and CORS default origins.
- `app_port` — port to run the server on (default 8000).

Create a `.env` file at the repo root in development to populate these values. `app/core/config.py` sets a few LANGCHAIN_* env vars automatically.

Example minimal `.env` (do NOT commit secrets):

```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
UPSTASH_REDIS_URL=https://.../0
UPSTASH_REDIS_TOKEN=...
QDRANT_URL=https://.../api
QDRANT_API_KEY=...
LANGCHAIN_API_KEY=...
JWT_SECRET_KEY=your-32-plus-char-secret
GITHUB_TOKEN=ghp_...
APP_ENV=development
APP_PORT=8000
```

---

## Install & run (development)

These instructions assume Windows PowerShell (your workspace uses PowerShell). Create and activate a virtual environment, install dependencies, and run the app with Uvicorn.

1) Create & activate venv

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
python -m pip install --upgrade pip; pip install -r requirements.txt
```

3) Provide environment variables (.env)

Create a `.env` file as shown above, or set environment variables in your shell.

4) Run database migrations (Postgres must be running and DATABASE_URL set)

```powershell
alembic upgrade head
```

5) Start the server

```powershell
# Use the app package path
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/docs` (if `APP_ENV` != production) to see interactive API docs.

Programmatic usage: the repository exposes an async `main()` in `app/main.py` decorated with `traceable`. Code can call that function directly to run graph-based workflows without going through HTTP.

---

## Running tests

Tests use pytest. Install test dependencies (included in `requirements.txt`) and run:

```powershell
pytest -q
```

Some tests may require a local/test Postgres instance or SQLite fallback (the requirements list `aiosqlite` for tests). Refer to `tests/conftest.py` for test fixtures and any required env vars.

---

## Database migrations

Alembic is configured with `alembic.ini` and the `migrations/` folder. Typical workflow:

1. Make model changes in `app/db/models.py`.
2. Create a migration:

```powershell
alembic revision --autogenerate -m "describe change"
```

3. Apply migrations:

```powershell
alembic upgrade head
```

---

## Development notes & tips

- The application relies on several external services (Postgres, Upstash Redis, Qdrant, various API keys). For local development, consider using Docker containers for Postgres and Qdrant, or use lightweight dev/test modes if available.
- The graph builder and checkpointing are central — if the graph fails to build, most flows won't run. Look in `app/graph/builder.py` and related modules for details.
- The `app/main.py` file contains the `lifespan` hook which initializes DB and graph state. If you need to run code directly (for debugging), call `app.state.graph.ainvoke(...)` after startup or use the exported `main()` async function.
- Middleware includes a Rate Limiter — tune it for dev/testing or disable it temporarily if it blocks local tests.

Edge cases to consider while developing:
- Missing/invalid environment variables (config validation raises helpful errors).
- Long-running graph runs — make sure timeouts and async behavior are handled.
- External API rate limits and credentials — tools depend on stable API keys.

---

## How pieces fit together (concise)

- API: FastAPI endpoints accept requests and translate them into session states.
- Graph: Encodes the agent workflow; invoked with an initial state and config.
- Agents: Implement specific steps and call LLMs and tools.
- RAG: Adds external knowledge via Qdrant-based vector search.
- Persistence: Postgres (structured state, checkpoints), Upstash Redis (ephemeral state / locks), and migrations via Alembic.

---

## Contributing

1. Fork the repo and create a feature branch.
2. Add tests for any new behavior.
3. Keep changes small and iterative (especially for agent logic).
4. Run tests and migrations locally before submitting a PR.

Please open issues describing the problem/feature and include logs and reproduction steps.

---

## License

This repository does not include a license file in the tree by default. Add a `LICENSE` file to indicate the intended license (MIT, Apache 2.0, etc.).

---

## Contact / Maintainer

Repository: `Coding-agent` (owner: SameerHandsome)

If you need help onboarding or running the project locally, open an issue or request a walkthrough.

---

End of README.
