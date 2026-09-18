"""
All LLM instances live here so the rest of the app never re-instantiates one.
"""
from langchain_groq import ChatGroq

from backend.config import GROQ_MODEL

# Main conversational model (tools are bound to it in nodes.py).
chat_llm = ChatGroq(model=GROQ_MODEL, temperature=0.4)

# Low-temperature model used for structured memory extraction.
memory_llm = ChatGroq(model=GROQ_MODEL, temperature=0)

# Low-temperature model used for the short "ChatGPT-style" thread titles.
title_llm = ChatGroq(model=GROQ_MODEL, temperature=0)
