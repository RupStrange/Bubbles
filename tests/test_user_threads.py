"""Unit tests for per-user thread scoping. Uses a tiny fake store - no Postgres or LLM needed."""
import itertools
import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.user_threads import (  # noqa: E402
    all_owned_thread_ids,
    list_user_thread_ids,
    register_thread,
    user_owns_thread,
)


class FakeStore:
    """Mimics the parts of BaseStore the module uses: get / put / search(prefix, limit, offset)."""

    def __init__(self):
        self._data = {}
        self._clock = itertools.count()

    def get(self, namespace, key):
        return self._data.get((namespace, key))

    def put(self, namespace, key, value):
        self._data[(namespace, key)] = SimpleNamespace(
            namespace=namespace, key=key, value=value, created_at=next(self._clock)
        )

    def search(self, prefix, limit=10, offset=0):
        hits = [it for (ns, _), it in self._data.items() if ns[: len(prefix)] == prefix]
        hits.sort(key=lambda it: it.created_at)
        return hits[offset : offset + limit]


def test_users_only_see_their_own_threads():
    store = FakeStore()
    register_thread(store, "alice", "t1")
    register_thread(store, "bob", "t2")
    register_thread(store, "alice", "t3")
    assert list_user_thread_ids(store, "alice") == ["t1", "t3"]
    assert list_user_thread_ids(store, "bob") == ["t2"]
    assert list_user_thread_ids(store, "nobody") == []


def test_user_id_prefix_does_not_leak():
    store = FakeStore()
    register_thread(store, "bob", "t1")
    register_thread(store, "bob2", "t2")
    assert list_user_thread_ids(store, "bob") == ["t1"]


def test_register_is_idempotent_and_keeps_order():
    store = FakeStore()
    register_thread(store, "alice", "t1")
    register_thread(store, "alice", "t2")
    register_thread(store, "alice", "t1")  # must not bump t1 after t2
    assert list_user_thread_ids(store, "alice") == ["t1", "t2"]


def test_ownership_check():
    store = FakeStore()
    register_thread(store, "alice", "t1")
    assert user_owns_thread(store, "alice", "t1")
    assert not user_owns_thread(store, "bob", "t1")


def test_pagination_beyond_default_limit():
    store = FakeStore()
    for i in range(250):
        register_thread(store, "alice", f"t{i}")
    assert len(list_user_thread_ids(store, "alice")) == 250


def test_all_owned_thread_ids_spans_users():
    store = FakeStore()
    register_thread(store, "alice", "t1")
    register_thread(store, "bob", "t2")
    assert all_owned_thread_ids(store) == {"t1", "t2"}
