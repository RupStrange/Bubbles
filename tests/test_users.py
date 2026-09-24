"""Unit tests for the user registry. Uses a tiny fake store - no Postgres or LLM needed."""
import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.users import DEFAULT_USER_ID, list_users, register_user, validate_user_id  # noqa: E402


class FakeStore:
    def __init__(self):
        self._data = {}

    def get(self, ns, key):
        return self._data.get((ns, key))

    def put(self, ns, key, value):
        self._data[(ns, key)] = SimpleNamespace(key=key, value=value)

    def search(self, prefix, limit=10, offset=0):
        hits = [it for (ns, _), it in self._data.items() if ns[: len(prefix)] == prefix]
        return hits[offset : offset + limit]

    def list_namespaces(self, *, prefix=None, max_depth=None, limit=100, offset=0):
        nss = {ns[:max_depth] if max_depth else ns for (ns, _) in self._data if ns[: len(prefix)] == prefix}
        return sorted(nss)[offset : offset + limit]


def test_default_user_always_listed():
    assert list_users(FakeStore()) == [DEFAULT_USER_ID]


def test_registered_and_legacy_users_are_discovered():
    store = FakeStore()
    register_user(store, "alice")
    register_user(store, "alice")  # idempotent
    store.put(("user", "bob", "details"), "f1", {"data": "likes tea"})      # legacy memory owner
    store.put(("user_threads", "carol"), "t1", {"thread_id": "t1"})         # legacy thread owner
    store.put(("users_extra", "nope"), "x", {})                             # must not match "user"
    assert list_users(store) == ["alice", "bob", "carol", DEFAULT_USER_ID]


def test_validate_user_id():
    assert validate_user_id("alice_01-x@y") is None
    assert validate_user_id("") is not None
    assert validate_user_id("a b") is not None
    assert validate_user_id("a.b") is not None
    assert validate_user_id("x" * 65) is not None
