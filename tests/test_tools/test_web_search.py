# tests/test_tools/test_web_search.py
import pytest
from unittest.mock import MagicMock, patch
from app.tools.web_search import WebSearchTool


@pytest.mark.asyncio
async def test_search_returns_list():
    tool = WebSearchTool()
    mock_results = [
        {
            "title": "FastAPI docs",
            "url": "https://fastapi.tiangolo.com",
            "content": "FastAPI is fast",
            "score": 0.9,
        }
    ]
    with patch.object(tool._client, "search", return_value={"results": mock_results}):
        results = await tool.search("FastAPI best practices")
        assert len(results) == 1
        assert results[0]["title"] == "FastAPI docs"


@pytest.mark.asyncio
async def test_search_fails_gracefully():
    """Tavily failure returns empty list, does not raise."""
    tool = WebSearchTool()
    with patch.object(tool._client, "search", side_effect=Exception("Tavily down")):
        results = await tool.search("anything")
        assert results == []
