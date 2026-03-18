# app/tools/web_search.py
# Uses tavily-python (pip install tavily-python==0.5.0)
# Called by orchestrator when PRD mentions unfamiliar frameworks.
# Also used by architect to look up latest best practices.
from tavily import TavilyClient
from app.core.config import settings
from typing import List, Dict
import asyncio, logging

logger = logging.getLogger(__name__)


class WebSearchTool:
    def __init__(self):
        self._client = TavilyClient(api_key=settings.tavily_api_key)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",  # "basic" | "advanced"
    ) -> List[Dict]:
        """
        Searches the web for current information.
        Returns list of {title, url, content, score} dicts.
        Used when PRD references technologies not in Qdrant RAG.
        Tavily is synchronous --- run in executor to avoid blocking.
        """
        loop = asyncio.get_event_loop()

        def _search():
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=True,
            )
            return response.get("results", [])

        try:
            return await loop.run_in_executor(None, _search)
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []  # fail gracefully --- agents continue without web context

    async def search_for_stack_docs(self, stack_name: str) -> str:
        """
        Convenience wrapper called by architect_node.
        Returns a single formatted string of web search results
        ready to inject into the architect prompt.
        """
        results = await self.search(
            query=f"{stack_name} project structure best practices 2024",
            max_results=3,
            search_depth="basic",
        )
        if not results:
            return "No web results found."

        parts = []
        for r in results:
            parts.append(f"Source: {r.get('url', '')}\n{r.get('content', '')[:400]}")
        return "\n\n".join(parts)


web_search_tool = WebSearchTool()
