# Make the project root importable when running `streamlit run frontend/app.py`
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from backend.graph import checkpointer, store, workflow
from backend.threads import ensure_thread_title, get_thread_title, retrieve_all_thread_ids

DEFAULT_USER_ID = "default_user"


# *********************************** Utility Functions *****************************************
def generate_thread_id() -> str:
    return str(uuid.uuid4())


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []


def add_thread(thread_id: str):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def load_conversation(thread_id: str):
    state = workflow.get_state(config={"configurable": {"thread_id": thread_id}}).values
    return state.get("messages", [])


def thread_label(thread_id: str) -> str:
    title = get_thread_title(store, thread_id)
    return title if title else f"New chat ({str(thread_id)[:8]})"


# ************************************ Session State *****************************************
if "user_id" not in st.session_state:
    st.session_state["user_id"] = DEFAULT_USER_ID
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []
if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_thread_ids(checkpointer)
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()
add_thread(st.session_state["thread_id"])


# *************************************** Sidebar UI *****************************************
st.set_page_config(page_title="Bubbles", page_icon="\U0001F4AC")
st.sidebar.title("\U0001F4AC Bubbles")

st.session_state["user_id"] = st.sidebar.text_input(
    "User ID (long-term memory key)",
    value=st.session_state["user_id"],
    help="Facts the assistant remembers about you are stored per user ID. "
    "Switch this to test how memory follows a user across threads.",
)

if st.sidebar.button("New Chat") and load_conversation(st.session_state["thread_id"]) != []:
    reset_chat()

st.sidebar.header("My Conversations")
for thread_id in reversed(st.session_state["chat_threads"]):
    if st.sidebar.button(thread_label(thread_id), key=f"thread_{thread_id}"):
        st.session_state["thread_id"] = thread_id
        messages = load_conversation(thread_id)
        st.session_state["message_history"] = [
            {"role": "user" if isinstance(m, HumanMessage) else "ai", "content": m.content}
            for m in messages
        ]


# ***************************************** Main UI *****************************************
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_message = st.chat_input("Type here")

if user_message:
    st.session_state["message_history"].append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.text(user_message)

    config = {
        "configurable": {
            "thread_id": st.session_state["thread_id"],
            "user_id": st.session_state["user_id"],
        }
    }
    response = workflow.stream(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
        stream_mode="messages",
    )

    def stream_generator():
        for message_chunk, metadata in response:
            if isinstance(message_chunk, AIMessage):  # only yield AI tokens
                yield message_chunk.content

    with st.chat_message("ai"):
        ai_message = st.write_stream(stream_generator())

    st.session_state["message_history"].append({"role": "ai", "content": ai_message})

    # ChatGPT-style: name the thread from its first exchange, once.
    ensure_thread_title(store, st.session_state["thread_id"], user_message, ai_message)
