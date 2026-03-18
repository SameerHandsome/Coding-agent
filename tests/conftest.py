# tests/conftest.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.models import Base
from app.main import app
from app.db.postgres import get_db
from app.core.security import create_access_token



@pytest.fixture(scope="function")
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_client(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_groq():
    """Mock ChatGroq returning valid orchestrator JSON."""
    resp = json.dumps(
        {
            "chosen_stack": {
                "name": "React+FastAPI",
                "frontend": "React",
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "extra": [],
            },
            "reasoning": "Good fit",
            "alternatives_considered": [
                {"stack": "Vue+Django", "score": 70, "rejected_because": "less popular"},
                {
                    "stack": "Next.js+Express",
                    "score": 65,
                    "rejected_because": "less stable",
                },
            ],
            "tasks_for_planner": ["Build auth", "Build API", "Build UI"],
        }
    )
    m = MagicMock()
    m.ainvoke = AsyncMock(return_value=resp)
    return m


@pytest.fixture
def mock_qdrant():
    m = MagicMock()
    m.search = AsyncMock(return_value=[])
    m.upsert = AsyncMock(return_value=None)
    m.ensure_collection = AsyncMock(return_value=None)
    return m


@pytest.fixture
def mock_redis():
    with patch("app.db.redis.check_rate_limit", return_value=True), patch(
        "app.db.redis.get_remaining_requests", return_value=5
    ):
        yield


@pytest.fixture
def mock_e2b():
    m = MagicMock()
    m.run_tests = AsyncMock(
        return_value={
            "passed": 5,
            "failed": 0,
            "errors": 0,
            "output": "5 passed",
            "success": True,
        }
    )
    m.run_linter = AsyncMock(
        return_value={"issues": [], "clean": True, "output": ""}
    )
    m.install_and_verify = AsyncMock(return_value=True)
    return m


@pytest.fixture
def mock_github():
    """Mock PyGithub tool --- no MCP server needed in tests."""
    m = MagicMock()
    m.create_repo = AsyncMock(return_value="testorg/test-project")
    m.push_files = AsyncMock(return_value="abc123sha")
    m.open_pull_request = AsyncMock(
        return_value="https://github.com/testorg/test-project/pull/1"
    )
    return m


@pytest.fixture
def mock_tavily():
    """Mock Tavily --- no real API calls in tests."""
    m = MagicMock()
    m.search = AsyncMock(return_value=[])
    m.search_for_stack_docs = AsyncMock(return_value="No web results in test mode.")
    return m


@pytest.fixture
def sample_prd():
    return (
        "Build a SaaS task management app with user authentication, "
        "REST API for CRUD operations on tasks, and a React frontend. "
        "Include role-based access control."
    )


@pytest.fixture
async def sample_user(test_db):
    from app.db.models import User
    from app.core.security import get_password_hash
    import uuid

    user = User(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        tier="free",
    )
    test_db.add(user)
    await test_db.commit()
    token = create_access_token({"sub": str(user.id), "tier": "free"})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}
