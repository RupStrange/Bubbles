"""
One-off script to create the Postgres tables used for short-term (checkpoints)
and long-term (store) memory.

Usage:
    docker compose up -d
    python scripts/init_db.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
