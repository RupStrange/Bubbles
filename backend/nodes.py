from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore

from backend.llm import chat_llm
from backend.memory import DEFAULT_USER_ID, get_user_details
from backend.prompts import SYSTEM_PROMPT_TEMPLATE
from backend.state import ChatState
from backend.tools import TOOLS

llm_with_tools = chat_llm.bind_tools(TOOLS)


def chat_node(state: ChatState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """LLM node that may answer directly or request a tool call. Personalized via long-term memory."""
    user_id = config.get("configurable", {}).get("user_id", DEFAULT_USER_ID)
    user_details = get_user_details(store, user_id) or "(empty)"

    system_message = SystemMessage(content=SYSTEM_PROMPT_TEMPLATE.format(user_details=user_details))
    response = llm_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}


tool_node = ToolNode(TOOLS)
