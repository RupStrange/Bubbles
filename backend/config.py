"""
Central place for all configuration / environment variables.
Nothing else in the app should call os.getenv() directly - import from here instead.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------- LLM -----
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # picked up automatically by ChatGroq

# ------------------------------------------------------------- Tools ------
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# ---------------------------------------------------------- Postgres ------
# Used for BOTH the short-term checkpointer (per-thread message history)
# and the long-term store (durable, cross-thread facts about a user).
POSTGRES_URI = os.getenv(
    "POSTGRES_URI",
    "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable",
)

# ----------------------------------------------------------- Titles -------
MAX_TITLE_WORDS = int(os.getenv("MAX_TITLE_WORDS", "6"))
