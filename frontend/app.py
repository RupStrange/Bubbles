# Make the project root importable when running `streamlit run frontend/app.py`
import os
import random
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from backend.graph import store, workflow
from backend.threads import ensure_thread_title, get_thread_title
from backend.users import list_users, register_user, validate_user_id
from backend.user_threads import list_user_thread_ids, register_thread, user_owns_thread

DEFAULT_USER_ID = "default_user"
BOT_AVATAR = "\U0001F4AC"  # speech balloon, matches the app icon
USER_AVATAR = "\U0001F9D1"  # generic person

# Cute little rotating "thinking" messages shown while Bubbles replies.
LOADING_MESSAGES = [
    "\U0001F4AD Bubbles is thinking...",
    "\U0001FAE7 Blowing a fresh bubble...",
    "\u2728 Sprinkling some magic...",
    "\U0001F9E0 Connecting the dots...",
    "\U0001F52E Reading the tea leaves...",
]


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


def start_session_for_user(user_id: str):
    """
    Gives `user_id` a fresh window: loads only THEIR saved conversations into the
    sidebar and opens a new blank thread. Called on first load and whenever the
    User ID field changes, so no one else's threads or messages linger on screen.
    """
    st.session_state["user_id"] = user_id
    st.session_state["user_select"] = user_id  # keeps the dropdown in sync
    st.session_state["chat_threads"] = list_user_thread_ids(store, user_id)
    st.session_state["thread_id"] = generate_thread_id()
    add_thread(st.session_state["thread_id"])
    st.session_state["message_history"] = []


def on_select_user():
    start_session_for_user(st.session_state["user_select"])
    st.toast(f"Switched to **{st.session_state['user_id']}** \U0001F44B", icon="\U0001F504")


def on_create_user():
    name = st.session_state.get("new_user_name", "").strip()
    error = validate_user_id(name)
    if error:
        st.session_state["create_user_error"] = error
        return
    register_user(store, name)
    st.session_state["create_user_error"] = None
    st.session_state["new_user_name"] = ""
    start_session_for_user(name)
    st.toast(f"Welcome, **{name}**! \U0001F389", icon="\U0001F38A")


def on_new_chat():
    if load_conversation(st.session_state["thread_id"]) != []:
        reset_chat()
        st.toast("Fresh chat started \U0001F195", icon="\U0001FAE7")


def switch_thread(thread_id: str):
    st.session_state["thread_id"] = thread_id
    # Only load history for threads this user owns (the blank, not-yet-saved
    # "New chat" thread has no owner record and no messages).
    owned = user_owns_thread(store, st.session_state["user_id"], thread_id)
    messages = load_conversation(thread_id) if owned else []
    st.session_state["message_history"] = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in messages
    ]


def thread_label(thread_id: str) -> str:
    title = get_thread_title(store, thread_id)
    if title:
        return title[:40] + ("\u2026" if len(title) > 40 else "")
    return f"New chat ({str(thread_id)[:8]})"


# ************************************ Session State *****************************************
if "user_id" not in st.session_state:
    start_session_for_user(DEFAULT_USER_ID)


# *************************************** Sidebar UI *****************************************
st.set_page_config(page_title="Bubbles", page_icon=BOT_AVATAR, layout="wide")

with st.sidebar:
    st.title(f"{BOT_AVATAR} Bubbles")
    st.caption("Your conversations, remembered. \U0001FAE7")

    known_users = list_users(store)
    if st.session_state["user_id"] not in known_users:
        known_users.append(st.session_state["user_id"])

    st.selectbox(
        "User",
        known_users,
        key="user_select",
        on_change=on_select_user,
        help="Each user has their own long-term memory and conversation list. "
        "Pick one to switch to their fresh window.",
    )

    with st.expander("\u2795 Create new user"):
        st.text_input("New user name", key="new_user_name", placeholder="e.g. alice")
        st.button("Create & switch", on_click=on_create_user, use_container_width=True)
        if st.session_state.get("create_user_error"):
            st.error(st.session_state["create_user_error"])

    st.divider()

    st.button("\u2795 New Chat", use_container_width=True, type="primary", on_click=on_new_chat)

    st.header("My Conversations", divider="violet")

    if not st.session_state["chat_threads"]:
        st.caption("No conversations yet \u2014 say hi below \U0001F44B")
    else:
        st.caption(f"\U0001FAE7 {len(st.session_state['chat_threads'])} conversation(s)")
        for thread_id in reversed(st.session_state["chat_threads"]):
            is_active = thread_id == st.session_state["thread_id"]
            st.button(
                ("\U0001F4AC " if is_active else "") + thread_label(thread_id),
                key=f"thread_{thread_id}",
                on_click=switch_thread,
                args=(thread_id,),
                use_container_width=True,
                type="primary" if is_active else "secondary",
            )

    st.divider()
    st.markdown(f"Signed in as :violet-background[**{st.session_state['user_id']}**]")


# ***************************************** Main UI *****************************************
current_title = thread_label(st.session_state["thread_id"]) if st.session_state["message_history"] else "New chat"
st.header(f"{BOT_AVATAR} {current_title}", divider="rainbow")

chat_container = st.container(height=520, border=False)

with chat_container:
    if not st.session_state["message_history"]:
        st.info("Start the conversation \u2014 ask me anything, I'll remember it for next time.")
        st.markdown(":violet[\U0001FAE7 \U0001FAE7 \U0001FAE7]")

    for message in st.session_state["message_history"]:
        avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

user_message = st.chat_input("Type here")

if user_message:
    st.session_state["message_history"].append({"role": "user", "content": user_message})
    with chat_container:
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(user_message)

    # First message in a thread: record who owns it so it shows up in their sidebar.
    register_thread(store, st.session_state["user_id"], st.session_state["thread_id"])
    had_title_before = get_thread_title(store, st.session_state["thread_id"]) is not None

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

    with chat_container:
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            with st.spinner(random.choice(LOADING_MESSAGES)):
                ai_message = st.write_stream(stream_generator())

    st.session_state["message_history"].append({"role": "assistant", "content": ai_message})

    # ChatGPT-style: name the thread from its first exchange, once.
    ensure_thread_title(store, st.session_state["thread_id"], user_message, ai_message)

    # Little celebration the first time a chat gets its name.
    if not had_title_before:
        st.balloons()

    st.rerun()
