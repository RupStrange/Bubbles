"""
Owns the single Postgres connection pool and hands out the two persistence
objects LangGraph needs:

  - checkpointer (PostgresSaver): SHORT-TERM memory - the full message
    history of one conversation thread. Keyed by thread_id.

  - store (PostgresStore): LONG-TERM memory - durable facts about a user
    (name, preferences, ongoing projects...) that persist across threads.
    Keyed by (namespace, key), e.g. (("user", user_id, "details"), fact_id).

Both share one connection pool so the app only talks to one database.
"""
from typing import Optional

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

from backend.config import POSTGRES_URI

# autocommit + row_factory=dict_row are required by langgraph's postgres
# implementations when you hand them a connection/pool yourself.
_POOL_KWARGS = {"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}

_pool: Optional[ConnectionPool] = None
_checkpointer: Optional[PostgresSaver] = None
_store: Optional[PostgresStore] = None
_initialized = False


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=POSTGRES_URI, max_size=10, kwargs=_POOL_KWARGS)
    return _pool


def get_checkpointer() -> PostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = PostgresSaver(_get_pool())
    return _checkpointer


def get_store() -> PostgresStore:
    global _store
    if _store is None:
        _store = PostgresStore(_get_pool())
    return _store


def init_db() -> None:
    """
    Creates the checkpoint + store tables if they don't exist yet (idempotent).

    In a larger production setup you'd run this once as a migration step
    (e.g. `python scripts/init_db.py`) rather than on every app boot - it's
    called here too purely for local-dev convenience.
    """
    global _initialized
    if _initialized:
        return
    get_checkpointer().setup()
    get_store().setup()
    _initialized = True
