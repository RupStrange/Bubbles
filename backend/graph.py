"""
Assembles the LangGraph workflow:

    START -> remember -> chat_node --(tool call?)--> tools -> chat_node -> END
                                  \\--(no tool call)--> END

- `remember` (backend/memory.py) writes any new durable facts to LONG-TERM memory.
- `chat_node` (backend/nodes.py) reads that memory to personalize its system prompt,
  and can call tools via the `tools` node.
- SHORT-TERM memory (full message history per thread) is handled transparently by
  the Postgres checkpointer passed to `.compile()`.
"""
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from backend.db import get_checkpointer, get_store, init_db
from backend.memory import remember_node
from backend.nodes import chat_node, tool_node
from backend.state import ChatState

# Idempotent: creates the checkpoint/store tables if they don't exist yet.
init_db()

checkpointer = get_checkpointer()
store = get_store()

graph = StateGraph(ChatState)
graph.add_node("remember", remember_node)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "remember")
graph.add_edge("remember", "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)  # -> "tools" or END
graph.add_edge("tools", "chat_node")

workflow = graph.compile(checkpointer=checkpointer, store=store)
