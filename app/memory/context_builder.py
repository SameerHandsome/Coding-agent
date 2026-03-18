# app/memory/context_builder.py
from app.tools.token_counter import count_tokens
from typing import List, Dict

MAX_CONTEXT_TOKENS = 6000


class ContextBuilder:
    def check_token_budget(self, context: Dict, max_tokens: int = MAX_CONTEXT_TOKENS) -> Dict:
        """Trim context to stay under token budget. Runs in memory_load_node ONCE."""
        if self._count(context) <= max_tokens:
            return context

        if len(context.get("rag_context", [])) > 3:
            context["rag_context"] = context["rag_context"][:3]

        if self._count(context) > max_tokens and len(context.get("chat_history", [])) > 5:
            context["chat_history"] = context["chat_history"][-5:]

        return context

    def format_rag_for_prompt(self, chunks: List[Dict]) -> str:
        if not chunks:
            return "No relevant patterns found."
        parts = []
        for i, c in enumerate(chunks, 1):
            content = c.get("content", c.get("fix", c.get("error", "")))
            parts.append(
                f"[{i}] type={c.get('type', '')} stack={c.get('stack', '')}\n{content}"
            )
        return "\n\n".join(parts)

    def format_hitl_for_prompt(self, decisions: List[Dict]) -> str:
        if not decisions:
            return "No prior decisions."
        return "\n".join(
            f" {d['checkpoint']}: {'APPROVED' if d['approved'] else 'REJECTED'}"
            f"{(' --- ' + d['feedback']) if d.get('feedback') else ''}"
            for d in decisions
        )

    def _count(self, context: Dict) -> int:
        total = 0
        for v in context.values():
            if isinstance(v, str):
                total += count_tokens(v)
            elif isinstance(v, list):
                total += sum(count_tokens(str(i)) for i in v)
        return total


context_builder = ContextBuilder()
