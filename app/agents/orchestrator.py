# app/agents/orchestrator.py
from app.core.llm import orchestrator_llm
from app.prompts.orchestrator import orchestrator_prompt
from langchain_core.output_parsers import StrOutputParser

orchestrator_chain = orchestrator_prompt | orchestrator_llm | StrOutputParser()
