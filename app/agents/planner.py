# app/agents/planner.py
from app.core.llm import orchestrator_llm
from app.prompts.planner import planner_prompt
from langchain_core.output_parsers import StrOutputParser

planner_chain = planner_prompt | orchestrator_llm | StrOutputParser()
