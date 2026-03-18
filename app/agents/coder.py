# app/agents/coder.py
from app.core.llm import coder_llm
from app.prompts.coder import coder_prompt
from langchain_core.output_parsers import StrOutputParser

coder_chain = coder_prompt | coder_llm | StrOutputParser()
