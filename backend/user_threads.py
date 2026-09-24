"""
Per-user thread ownership.

The checkpointer (short-term memory) only knows about `thread_id`s - it has no
idea which user a thread belongs to. This module adds that missing link so the
sidebar can show only the *current* user's conversations.

Storage layout (in the same Postgres `store` used for long-term memory):

    namespace: ("user_threads", <user_id>)
    key:       <thread_id>
    value:     {"thread_id": <thread_id>}

The store stamps every item with `created_at`, which is what we sort by, so the
sidebar order no longer depends on set/dict iteration order.

A thread is registered the first time the user actually sends a message in it
(not when the empty "New chat" is created), so blank conversations never
litter the database.

NOTE: this is bookkeeping, not security. `user_id` is still a free-text field,
so anyone who types someone else's ID sees their threads. Real access control
needs real authentication (see README -> Extending Bubbles).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:  # keeps this module importable without langgraph installed (tests)
    from langgraph.store.base import BaseStore

USER_THREADS_ROOT = "user_threads"
_PAGE_SIZE = 100  # store.search() returns only 10 items unless you ask for more


def user_threads_namespace(user_id: str) -> tuple:
    return (USER_THREADS_ROOT, user_id)


def register_thread(store: "BaseStore", user_id: str, thread_id: str) -> None:
    """Records that `thread_id` belongs to `user_id`. Idempotent (keeps original created_at)."""
    ns = user_threads_namespace(user_id)
    if store.get(ns, str(thread_id)) is None:
        store.put(ns, str(thread_id), {"thread_id": str(thread_id)})


def user_owns_thread(store: "BaseStore", user_id: str, thread_id: str) -> bool:
    return store.get(user_threads_namespace(user_id), str(thread_id)) is not None


def _search_all(store: "BaseStore", namespace_prefix: tuple) -> list:
    items, offset = [], 0
    while True:
        page = store.search(namespace_prefix, limit=_PAGE_SIZE, offset=offset)
        items.extend(page)
        if len(page) < _PAGE_SIZE:
            return items
        offset += _PAGE_SIZE


def list_user_thread_ids(store: "BaseStore", user_id: str) -> List[str]:
    """This user's thread_ids, oldest first (the sidebar renders them newest first)."""
    items = _search_all(store, user_threads_namespace(user_id))
    items.sort(key=lambda it: it.created_at)
    return [it.key for it in items]


def all_owned_thread_ids(store: "BaseStore") -> Set[str]:
    """Every thread_id that has an owner, across all users (used by the migration script)."""
    return {it.key for it in _search_all(store, (USER_THREADS_ROOT,))}
