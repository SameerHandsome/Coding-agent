# app/tools/token_counter.py
import tiktoken
from typing import List, Dict

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def count_messages_tokens(messages: List[Dict]) -> int:
    return sum(
        count_tokens(m.get("role", "")) + count_tokens(m.get("content", "")) + 4
        for m in messages
    )


def trim_to_token_limit(text: str, max_tokens: int) -> str:
    tokens = _enc.encode(text)
    return _enc.decode(tokens[:max_tokens]) if len(tokens) > max_tokens else text
