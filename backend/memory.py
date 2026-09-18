"""
Long-term memory (LTM): durable, cross-thread facts about a user.

Backed by the Postgres `store` (see db.py), namespaced as
("user", user_id, "details") -> {fact_id: {"data": "<atomic fact>"}}.
"""
import uuid
from typing import List

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from backend.llm import memory_llm
from backend.prompts import MEMORY_EXTRACTION_PROMPT
from backend.state import ChatState

DEFAULT_USER_ID = "default_user"


class MemoryItem(BaseModel):
    text: str = Field(description="A single atomic fact about the user")
    is_new: bool = Field(description="True if new info, false if it duplicates existing memory")


class MemoryDecision(BaseModel):
    should_write: bool
    memories: List[MemoryItem] = Field(default_factory=list)


memory_extractor = memory_llm.with_structured_output(MemoryDecision)


def memory_namespace(user_id: str) -> tuple:
    return ("user", user_id, "details")


def get_user_details(store: BaseStore, user_id: str) -> str:
    """Returns all known facts about a user as a newline-joined string ("" if none)."""
    items = store.search(memory_namespace(user_id))
    if not items:
        return ""
    return "\n".join(it.value.get("data", "") for it in items)


def remember_node(state: ChatState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """
    Graph node: looks at the latest human message, decides whether it contains
    anything worth remembering long-term, and writes new facts to the store.
    Runs once per turn, before the chat node, and never blocks the chat flow.
    """
    user_id = config.get("configurable", {}).get("user_id", DEFAULT_USER_ID)

    last_message = state["messages"][-1] if state["messages"] else None
    if last_message is None or last_message.type != "human" or not last_message.content:
        return {}

    existing = get_user_details(store, user_id) or "(empty)"

    try:
        decision: MemoryDecision = memory_extractor.invoke(
            [
                SystemMessage(content=MEMORY_EXTRACTION_PROMPT.format(user_details=existing)),
                {"role": "user", "content": last_message.content},
            ]
        )
    except Exception:
        # A memory-extraction hiccup should never break the actual chat response.
        return {}

    if decision.should_write:
        ns = memory_namespace(user_id)
        for mem in decision.memories:
            if mem.is_new and mem.text.strip():
                store.put(ns, str(uuid.uuid4()), {"data": mem.text.strip()})

    return {}
