# app/api/middleware/input_filter.py
import re
from typing import TypedDict


class FilterResult(TypedDict):
    clean: bool
    reason: str


INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"you are now a",
    r"act as a",
    r"act as if",
    r"jailbreak",
    r"DAN mode",
    r"forget your instructions",
    r"disregard your",
    r"bypass your",
    r"pretend you are",
    r"new persona",
    r"system prompt",
]

MALICIOUS_PATTERNS = [
    r"rm\s+-rf",
    r"DROP\s+TABLE",
    r"DROP\s+DATABASE",
    r"exec\s*\(",
    r"eval\s*\(",
    r"<script",
    r"javascript:",
    r"__import__",
    r"os\.system",
    r"subprocess",
    r"shell=True",
    r"base64\.decode",
    r"pickle\.loads",
]

PII_PATTERNS = [
    r"\d{16}",
    r"\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    r"\d{3}-\d{2}-\d{4}",
    r"\d{3}[.\s-]\d{3}[.\s-]\d{4}",
]


def filter_input(text: str) -> FilterResult:
    if len(text) < 20:
        return {"clean": False, "reason": "invalid_length_too_short"}
    if len(text) > 10000:
        return {"clean": False, "reason": "invalid_length_too_long"}

    lower = text.lower()
    for p in INJECTION_PATTERNS:
        if re.search(p, lower, re.IGNORECASE):
            return {"clean": False, "reason": "prompt_injection"}

    for p in MALICIOUS_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return {"clean": False, "reason": "malicious_content"}

    for p in PII_PATTERNS:
        if re.search(p, text):
            return {"clean": False, "reason": "pii_detected"}

    return {"clean": True, "reason": ""}
