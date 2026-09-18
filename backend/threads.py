"""
Thread bookkeeping: listing known threads and giving each one a short,
auto-generated title (the way ChatGPT names a new chat from its first
exchange), stored as long-term data in the same Postgres store used for
user memory.
"""
from typing import List, Optional

from langgraph.store.base import BaseStore

from backend.config import MAX_TITLE_WORDS
from backend.llm import title_llm
from backend.prompts import TITLE_GENERATION_PROMPT

THREAD_TITLE_NAMESPACE = ("thread_titles",)


def retrieve_all_thread_ids(checkpointer) -> List[str]:
    """Every distinct thread_id the checkpointer has ever seen."""
    thread_ids = set()
    for checkpoint in checkpointer.list(None):
        thread_ids.add(checkpoint.config["configurable"]["thread_id"])
    return list(thread_ids)


def get_thread_title(store: BaseStore, thread_id: str) -> Optional[str]:
    item = store.get(THREAD_TITLE_NAMESPACE, str(thread_id))
    return item.value.get("title") if item else None


def set_thread_title(store: BaseStore, thread_id: str, title: str) -> None:
    store.put(THREAD_TITLE_NAMESPACE, str(thread_id), {"title": title})


def _sanitize_title(raw: str, max_words: int) -> str:
    title = (raw or "").strip().strip('"').strip("'")
    title = title.splitlines()[0].strip() if title else title
    words = title.split()
    if len(words) > max_words:
        title = " ".join(words[:max_words])
    return title or "New chat"


def generate_thread_title(user_message: str, ai_message: str) -> str:
    """Summarizes the first exchange of a thread into a short title (LLM call)."""
    prompt = TITLE_GENERATION_PROMPT.format(
        max_words=MAX_TITLE_WORDS,
        user_message=(user_message or "")[:500],
        ai_message=(ai_message or "")[:500],
    )
    try:
        response = title_llm.invoke(prompt)
        return _sanitize_title(response.content, MAX_TITLE_WORDS)
    except Exception:
        # Fall back to a trimmed version of the user's own message.
        return _sanitize_title(user_message, MAX_TITLE_WORDS)


def ensure_thread_title(store: BaseStore, thread_id: str, user_message: str, ai_message: str) -> str:
    """Returns the thread's title, generating + persisting one the first time this is called."""
    existing = get_thread_title(store, thread_id)
    if existing:
        return existing
    title = generate_thread_title(user_message, ai_message)
    set_thread_title(store, thread_id, title)
    return title
