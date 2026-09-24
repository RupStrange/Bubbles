"""
User registry: which user IDs exist, and creating new ones.

Users are recorded under the namespace ("users",) in the Postgres store
(key = user_id). For convenience, `list_users` also discovers users who already
have long-term memory or saved threads from before this registry existed, so
nobody has to be re-created.

Note: DEFAULT_USER_ID must match backend/memory.py (kept separate here so this
module doesn't pull in the LLM clients).
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

DEFAULT_USER_ID = "default_user"
USERS_NAMESPACE = ("users",)
MAX_USER_ID_LEN = 64
# LangGraph store namespace labels can't contain periods, so keep IDs to a safe set.
_VALID_USER_ID = re.compile(r"^[A-Za-z0-9_\-@]+$")
_PAGE = 100


def validate_user_id(raw: str) -> Optional[str]:
    """Returns an error message, or None if `raw` is a usable user ID."""
    if not raw:
        return "Enter a user name."
    if len(raw) > MAX_USER_ID_LEN:
        return f"Keep it under {MAX_USER_ID_LEN} characters."
    if not _VALID_USER_ID.match(raw):
        return "Use only letters, numbers, '_', '-' and '@' (no spaces or dots)."
    return None


def register_user(store: "BaseStore", user_id: str) -> None:
    """Idempotent."""
    if store.get(USERS_NAMESPACE, user_id) is None:
        store.put(USERS_NAMESPACE, user_id, {"user_id": user_id})


def _registered(store: "BaseStore") -> Set[str]:
    found, offset = set(), 0
    while True:
        page = store.search(USERS_NAMESPACE, limit=_PAGE, offset=offset)
        found.update(it.key for it in page)
        if len(page) < _PAGE:
            return found
        offset += _PAGE


def _users_from_namespaces(store: "BaseStore", root: str) -> Set[str]:
    """Distinct user IDs seen under ("<root>", <user_id>, ...) namespaces."""
    found, offset = set(), 0
    while True:
        page = store.list_namespaces(prefix=(root,), max_depth=2, limit=_PAGE, offset=offset)
        found.update(ns[1] for ns in page if len(ns) >= 2)
        if len(page) < _PAGE:
            return found
        offset += _PAGE


def list_users(store: "BaseStore") -> List[str]:
    """All known user IDs, sorted, with the default user always present."""
    users = {DEFAULT_USER_ID}
    users |= _registered(store)
    users |= _users_from_namespaces(store, "user")          # long-term memory owners
    users |= _users_from_namespaces(store, "user_threads")  # thread owners
    return sorted(users, key=str.lower)
