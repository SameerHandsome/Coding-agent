# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi          # ADDED for custom OpenAPI schema
from fastapi.security import HTTPBearer                 # ADDED for Bearer token in Swagger
from langsmith import traceable
from app.core.config import settings
from app.db.postgres import init_db, close_db
from app.graph.builder import build_graph
from app.rag.hybrid_search import hybrid_searcher
from app.api.middleware.rate_limiter import RateLimiterMiddleware
from app.api.routes import auth, session, hitl, user
from app.graph.builder import build_graph, close_checkpointer
import logging

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting App Builder Agent v4...")
    await init_db()
    app.state.graph = await build_graph()
    await hybrid_searcher.ensure_collection()
    logger.info("Ready --- No MCP. Direct SDKs only.")
    yield
    await close_checkpointer()    # ADD THIS
    await close_db()
    logger.info("Shutdown complete")


security = HTTPBearer()                                 # ADDED - registers Bearer scheme

app = FastAPI(
    title="App Builder Agent",
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
)

app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if settings.app_env == "development" else ["https://yourdomain.com"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
app.include_router(hitl.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0", "env": settings.app_env}


# ADDED - custom OpenAPI schema so Swagger shows HTTPBearer input instead of OAuth2 form
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
        }
    }
    for path in schema["paths"].values():
        for method in path.values():
            method["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi


@traceable(name="app_builder_main", run_type="chain")
async def main(
    prd_content: str,
    session_id: str,
    user_id: str,
    user_tier: str = "free",
) -> dict:
    config = {"configurable": {"thread_id": session_id}}
    from app.api.routes.session import _empty_state
    initial = _empty_state(user_id, session_id, user_tier, prd_content, "project")
    return await app.state.graph.ainvoke(initial, config=config)