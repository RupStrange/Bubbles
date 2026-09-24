"""
One-off migration: assigns every existing thread that has no owner to a user.

Threads created before per-user scoping have no owner record, so they would
vanish from every sidebar. Run this once to claim them for a user (default:
"default_user"). Safe to re-run - already-owned threads are left alone.

Usage:
    python scripts/migrate_thread_owners.py                 # -> default_user
    python scripts/migrate_thread_owners.py --user alice    # -> alice
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_checkpointer, get_store, init_db  # noqa: E402
from backend.memory import DEFAULT_USER_ID  # noqa: E402
from backend.threads import retrieve_all_thread_ids  # noqa: E402
from backend.user_threads import all_owned_thread_ids, register_thread  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--user", default=DEFAULT_USER_ID, help="user_id that will own the orphaned threads")
    args = parser.parse_args()

    init_db()
    store = get_store()

    owned = all_owned_thread_ids(store)
    orphans = [t for t in retrieve_all_thread_ids(get_checkpointer()) if t not in owned]
    for thread_id in orphans:
        register_thread(store, args.user, thread_id)
    print(f"Assigned {len(orphans)} orphaned thread(s) to user '{args.user}'.")


if __name__ == "__main__":
    main()
