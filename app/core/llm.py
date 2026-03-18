# app/core/llm.py
from langchain_groq import ChatGroq
from app.core.config import settings

# Orchestrator + Planner --- creative decisions
orchestrator_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=settings.groq_api_key,
    max_tokens=4096,
    timeout=120,
    max_retries=5,
)

# Architect + All 3 Coders --- precise code generation
coder_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=settings.groq_api_key,
    max_tokens=4096,  # Reduced from 8192 to avoid truncation from rate limits
    timeout=120,
    max_retries=5,
)

# Reflexion --- debugging needs slight creativity
reflexion_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=settings.groq_api_key,
    max_tokens=4096,
    timeout=120,
    max_retries=5,
)