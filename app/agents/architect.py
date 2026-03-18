# app/agents/architect.py
from app.core.llm import coder_llm
from app.prompts.architect import architect_prompt
from langchain_core.output_parsers import StrOutputParser

architect_chain = architect_prompt | coder_llm | StrOutputParser()
