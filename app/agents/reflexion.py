# app/agents/reflexion.py
from app.core.llm import reflexion_llm
from app.prompts.reflexion import reflexion_prompt
from langchain_core.output_parsers import StrOutputParser

reflexion_chain = reflexion_prompt | reflexion_llm | StrOutputParser()
