# 💬 Bubbles

A LangGraph-powered chatbot with **short-term memory**, **long-term memory**,
**tool calling**, and **ChatGPT-style auto-titled conversations** — built on
Streamlit, Groq, and Postgres.

This started as a two-file prototype (`6.app_tools.py` for the UI,
`chatbot_backend_tools_6.py` for the graph) and was rebuilt into a modular,
production-style project called **Bubbles**.

---

## Table of contents

- [What it does](#what-it-does)
- [Architecture at a glance](#architecture-at-a-glance)
- [How memory works](#how-memory-works)
- [How thread titles work](#how-thread-titles-work)
- [Project structure](#project-structure)
- [File-by-file reference](#file-by-file-reference)
- [Requirements](#requirements)
- [Setup](#setup)
- [Environment variables](#environment-variables)
- [Running the app](#running-the-app)
- [Using the app](#using-the-app)
- [Multi-user notes](#multi-user-notes)
- [Troubleshooting](#troubleshooting)
- [Extending Bubbles](#extending-bubbles)
- [What changed from the original prototype](#what-changed-from-the-original-prototype)

---

## What it does

Bubbles is a chat assistant that:

- Answers questions directly, or calls a **tool** (web search, weather,
  stock price, calculator) when that gives a better answer.
- Remembers the **full history of each conversation** (short-term memory),
  so you can close the tab and come back to a thread later.
- Remembers **durable facts about you** — your name, preferences, ongoing
  projects — and carries them **across every conversation you start**
  (long-term memory), the same way a human assistant would remember things
  about you between meetings.
- **Auto-names each conversation** from its first exchange, the way ChatGPT
  or Claude name a new chat, so your sidebar is readable instead of a wall
  of UUIDs.

Everything is backed by a single Postgres database, run via `docker-compose`.

---

## Architecture at a glance

```
┌─────────────┐        ┌───────────────────────────────────────────┐
│  Streamlit   │  HTTP  │                 LangGraph                 │
│  frontend    │◄──────►│                                           │
│ (frontend/   │        │   START                                   │
│   app.py)    │        │     │                                     │
└─────────────┘        │     ▼                                     │
                        │  remember  ──► writes new facts to LTM     │
                        │     │           (Postgres store)           │
                        │     ▼                                     │
                        │  chat_node ──► reads LTM, builds prompt,   │
                        │     │  ▲        calls the LLM               │
                        │     │  │                                   │
                        │     ▼  │ loop while tool calls requested   │
                        │   tools ┘  (search / weather / stock /     │
                        │            calculator)                     │
                        │     │                                     │
                        │     ▼                                     │
                        │    END                                    │
                        └───────────────────────────────────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────────────────┐
                        │              Postgres (docker)             │
                        │  ┌─────────────────┐  ┌──────────────────┐ │
                        │  │  checkpointer    │  │      store       │ │
                        │  │  (short-term)    │  │   (long-term)    │ │
                        │  │  full message    │  │  user facts +    │ │
                        │  │  history / thread│  │  thread titles   │ │
                        │  └─────────────────┘  └──────────────────┘ │
                        └───────────────────────────────────────────┘
```

Every user turn runs through the **whole graph once**: `remember` fires
first (looks at what you just said and decides whether anything is worth
remembering long-term), then `chat_node` responds, calling `tools` in a loop
for as many tool calls as it needs before producing a final answer.

---

## How memory works

Bubbles has **two separate, deliberately different** kinds of memory. This is
the most important concept in the whole project.

### Short-term memory (STM) — "what was said in this conversation"

- Implemented by LangGraph's `PostgresSaver` **checkpointer**.
- Scope: one **thread** (one conversation).
- Contains: the full list of messages (human, AI, tool calls, tool results)
  for that thread.
- Managed automatically — you never write to it directly. Every time the
  graph runs, LangGraph appends the new messages to the thread's checkpoint.
- This is what makes "New Chat" vs. clicking back into an old conversation
  work — `workflow.get_state(...)` pulls a thread's full history back out.

### Long-term memory (LTM) — "what I know about you"

- Implemented by LangGraph's `PostgresStore`.
- Scope: one **user** (`user_id`), shared across *all* of their threads.
- Contains: short, atomic facts like `"User's name is Nitish."` or
  `"User is building a RAG chatbot with LangGraph."`
- Managed by `backend/memory.py`:
  - `remember_node` runs on every single turn, before the chat model
    responds. It sends your latest message plus everything already known
    about you to a small, `temperature=0` LLM call that returns structured
    output (`MemoryDecision`) — basically "here are 0+ new atomic facts,
    and here's which ones are genuinely new vs. already known."
  - Anything flagged `is_new=True` gets written to the store.
  - `chat_node` then reads all known facts about the user and drops them
    into the system prompt, so the assistant can say things like
    *"Sure, Nitish — since you're using LangGraph already..."* instead of
    treating you like a stranger every time.
- **Fails safe**: if the memory-extraction LLM call errors for any reason,
  `remember_node` just returns `{}` — it can never break or delay your
  actual chat response.

### Why they're stored separately (but in the same database)

They're logically separate (different LangGraph primitives, different
namespaces, different lifetimes) but physically share **one Postgres
instance and one connection pool** (`backend/db.py`), so you only have to
run and back up a single database.

| | Short-term memory | Long-term memory |
|---|---|---|
| LangGraph object | `PostgresSaver` (checkpointer) | `PostgresStore` |
| Keyed by | `thread_id` | `user_id` |
| Grows with | messages in one conversation | facts learned about a person |
| Survives "New Chat"? | No — a new thread starts empty | Yes — it's global to the user |
| Who writes to it | LangGraph internals (automatic) | `remember_node` (LLM-decided) |

---

## How thread titles work

`backend/threads.py` handles this, and it's intentionally simple:

1. Titles are stored in the *same* Postgres store as long-term memory, just
   under a different namespace: `("thread_titles",)`, keyed by `thread_id`.
2. After every AI reply, the frontend calls
   `ensure_thread_title(store, thread_id, user_message, ai_message)`.
3. That function checks if a title already exists for the thread:
   - **Yes** → returns it immediately, no LLM call, no cost.
   - **No** → sends the first user message + first AI reply to a small LLM
     call with a short prompt ("name this conversation the way ChatGPT
     names a new chat, {N} words or fewer, no punctuation"), sanitizes the
     result (strips quotes, trims to the word limit, falls back to "New
     chat" if empty), and saves it.
4. The sidebar (`frontend/app.py`) reads the title back via
   `get_thread_title` and shows it as the button label for that thread. If
   no title exists yet (e.g. a thread with no messages), it falls back to
   `"New chat (1a2b3c4d)"` using the first 8 characters of the thread ID.

So each thread gets **exactly one** title-generation LLM call, the very
first time it has something to summarize — never on every message.

---

## Project structure

```
bubbles/
├── docker-compose.yml     # Spins up Postgres (used for both STM and LTM)
├── requirements.txt       # Python dependencies
├── .env.example            # Template for your local .env
├── README.md                # This file
├── scripts/
│   └── init_db.py            # One-off: create the Postgres tables
├── backend/
│   ├── __init__.py
│   ├── config.py              # Every env var, read once, imported everywhere else
│   ├── db.py                    # Connection pool + checkpointer/store factories
│   ├── llm.py                     # The 3 LLM instances (chat / memory / titles)
│   ├── tools.py                     # calculate, get_weather, get_stock_price, search
│   ├── state.py                       # ChatState TypedDict (the graph's schema)
│   ├── prompts.py                       # Every prompt template, in one place
│   ├── memory.py                          # Long-term memory: extraction node + reader
│   ├── nodes.py                             # chat_node (personalized) + tool_node
│   ├── threads.py                             # Thread listing + title generation
│   └── graph.py                                 # Wires everything into the compiled graph
└── frontend/
    └── app.py                                     # Streamlit UI
```

---

## File-by-file reference

### `backend/config.py`
The **only** file that calls `os.getenv(...)`. Loads `.env` via
`python-dotenv` and exposes typed constants (`GROQ_MODEL`, `POSTGRES_URI`,
`MAX_TITLE_WORDS`, etc.). Every other module imports from here instead of
reading the environment directly — keeps secrets/config centralized and
easy to audit.

### `backend/db.py`
Owns a single `psycopg_pool.ConnectionPool` pointed at `POSTGRES_URI`, and
hands out:
- `get_checkpointer()` → a `PostgresSaver` (short-term memory)
- `get_store()` → a `PostgresStore` (long-term memory)
- `init_db()` → idempotently creates both sets of tables (`CREATE TABLE IF
  NOT EXISTS` under the hood). Safe to call on every app start.

### `backend/llm.py`
Three `ChatGroq` instances, so nothing else in the app re-instantiates a
model:
- `chat_llm` (`temperature=0.4`) — the main conversational model, later
  bound to tools in `nodes.py`.
- `memory_llm` (`temperature=0`) — deterministic, used for structured fact
  extraction.
- `title_llm` (`temperature=0`) — deterministic, used for short title
  generation.

### `backend/tools.py`
The four tools the model can call:
- `search_tool` — DuckDuckGo web search.
- `calculate(n1, n2, operation)` — add/sub/mul/div, string inputs coerced
  to `float` (LLMs often pass numbers as strings).
- `get_weather(place)` — calls WeatherAPI.com, requires `WEATHER_API_KEY`.
- `get_stock_price(symbol)` — calls Alpha Vantage, requires
  `ALPHA_VANTAGE_API_KEY`.

Both API-backed tools return a clear `{"error": "..."}` dict instead of
crashing if the relevant key isn't configured — so the bot degrades
gracefully instead of throwing an exception mid-conversation.

### `backend/state.py`
The single `ChatState` TypedDict every node reads/writes:
```python
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```
`add_messages` is LangGraph's reducer that appends new messages instead of
overwriting the list.

### `backend/prompts.py`
Every prompt template as a plain string constant:
- `SYSTEM_PROMPT_TEMPLATE` — the assistant's persona + injected user memory.
- `MEMORY_EXTRACTION_PROMPT` — instructions for the fact-extraction LLM.
- `TITLE_GENERATION_PROMPT` — instructions for the title LLM.

Keeping these separate from logic makes them easy to tune without touching
any node code.

### `backend/memory.py`
- `MemoryItem` / `MemoryDecision` — Pydantic models used as **structured
  output** schemas (`memory_llm.with_structured_output(MemoryDecision)`).
- `get_user_details(store, user_id)` — reads all known facts about a user
  as a newline-joined string.
- `remember_node(state, config, *, store)` — the actual LangGraph node.
  Only acts on `human`-type messages, calls the memory-extraction LLM, and
  writes any new facts. Wrapped in `try/except` so it can never break the
  chat.

### `backend/nodes.py`
- `llm_with_tools = chat_llm.bind_tools(TOOLS)`
- `chat_node(state, config, *, store)` — builds the system prompt (with
  injected long-term memory), invokes the model with the full message
  history, and returns its response (which may include tool calls).
- `tool_node = ToolNode(TOOLS)` — LangGraph's prebuilt node that actually
  executes whichever tool(s) the model asked for.

### `backend/threads.py`
Everything about naming and listing conversations — see
[How thread titles work](#how-thread-titles-work) above. Also has
`retrieve_all_thread_ids(checkpointer)`, which scans the checkpointer for
every distinct `thread_id` it has ever seen (used to populate the sidebar
on load).

### `backend/graph.py`
The assembly file. Calls `init_db()`, gets the checkpointer + store, builds
the `StateGraph`:

```python
graph.add_edge(START, "remember")
graph.add_edge("remember", "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)  # -> "tools" or END
graph.add_edge("tools", "chat_node")

workflow = graph.compile(checkpointer=checkpointer, store=store)
```

`workflow`, `checkpointer`, and `store` are all exported from here and
imported directly by the frontend — there's no other place in the app that
constructs graph-related objects.

### `frontend/app.py`
The Streamlit UI:
- Sidebar: editable **User ID** field (the long-term-memory key), **New
  Chat** button, and a scrollable list of past conversations (labeled by
  their auto-generated title).
- Main pane: renders the current thread's message history, a chat input
  box, and streams the model's response token-by-token via
  `workflow.stream(..., stream_mode="messages")`.
- After every AI reply, calls `ensure_thread_title(...)` to (maybe) name
  the thread.

### `scripts/init_db.py`
A standalone CLI entry point that just calls `backend.db.init_db()` and
prints a confirmation. Useful for running the "create tables" step
explicitly and separately from app startup (a more typical production
pattern than relying on it happening automatically on import).

---

## Requirements

- **Python 3.11+** (Postgres client libraries here are tested against modern
  3.x; anything reasonably recent should work).
- **Docker** (or an existing Postgres 14+ instance you point at instead).
- A **Groq API key** — [console.groq.com](https://console.groq.com) — this
  is the only required external credential.
- *(Optional)* a **WeatherAPI.com** key and an **Alpha Vantage** key, only
  if you want the `get_weather` / `get_stock_price` tools to actually work.
  Without them, those two tools just return a clear error instead of
  crashing.

---

## Setup

```bash
# 1. Unzip / clone the project, then cd into it
cd bubbles

# 2. Start Postgres (reads docker-compose.yml)
docker compose up -d
# (older Docker installs: `docker-compose up -d`)

# 3. Create a virtual environment (recommended) and install dependencies
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Create your local env file
cp .env.example .env
# then open .env and fill in GROQ_API_KEY at minimum

# 5. (Optional but recommended) create the DB tables explicitly
python scripts/init_db.py

# 6. Run it
streamlit run frontend/app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) and
should open it in your browser automatically.

---

## Environment variables

All of these live in `.env` (copy `.env.example` to start). None of them
should ever be committed to source control.

| Variable | Required? | Default | What it's for |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** | — | Auth for every LLM call (chat, memory extraction, titles). Get one at console.groq.com. |
| `GROQ_MODEL` | No | `meta-llama/llama-4-scout-17b-16e-instruct` | Which Groq-hosted model to use for all three LLM roles. |
| `POSTGRES_URI` | No | `postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable` | Connection string for both short-term and long-term memory. Matches `docker-compose.yml` by default. |
| `WEATHER_API_KEY` | No | — | Enables the `get_weather` tool (weatherapi.com). Without it, the tool returns `{"error": "..."}`. |
| `ALPHA_VANTAGE_API_KEY` | No | — | Enables the `get_stock_price` tool (alphavantage.co). Without it, the tool returns `{"error": "..."}`. |
| `MAX_TITLE_WORDS` | No | `6` | Max word count for auto-generated thread titles. |

No quotes needed around values (`KEY=value`, not `KEY="value"`) unless the
value itself contains a `#` or a space — none of the defaults do.

---

## Running the app

```bash
streamlit run frontend/app.py
```

Run this from the **project root** (`bubbles/`), not from inside
`frontend/` — the script adds the project root to `sys.path` on the
assumption that's where it was launched from.

To stop: `Ctrl+C` in the terminal running Streamlit, and
`docker compose down` to stop Postgres (add `-v` to also delete all stored
data: `docker compose down -v`).

---

## Using the app

1. **User ID** (sidebar) — this is the key long-term memory is stored
   under. Leave it as `default_user` for solo use, or change it to test how
   memory differs between "users."
2. **New Chat** — starts a fresh thread with empty short-term memory (long-
   term memory about you still carries over, since that's user-scoped, not
   thread-scoped).
3. **My Conversations** (sidebar) — click any past thread to reload its
   full history. Threads are labeled with their auto-generated title once
   one exists.
4. **Chat box** — type normally. The model will call tools on its own when
   useful (e.g. "what's the weather in Kolkata?" or "search for the latest
   LangGraph release").
5. Tell it something about yourself (e.g. *"I'm building a RAG app with
   LangGraph"*) and start a **New Chat** — it should recall that fact in
   the new conversation, since it's stored in long-term memory.

---

## Multi-user notes

The original prototype had no concept of "user" — one anonymous Streamlit
session. Long-term memory needs *some* stable identity to attach facts to,
so Bubbles adds a plain **User ID** text field in the sidebar.

In a real deployment, you'd replace that text box with whatever your actual
auth system provides (a logged-in user's ID, an email, etc.) — nothing else
in the backend needs to change, since `user_id` is just threaded through
`config["configurable"]["user_id"]` on every graph invocation.

---

## Troubleshooting

**"connection refused" / can't reach Postgres**
Make sure `docker compose up -d` actually started the container
(`docker ps` should show `bubbles_postgres` running) and that
`POSTGRES_URI` in `.env` matches the port in `docker-compose.yml`
(`5442` by default, *not* Postgres's usual `5432`).

**`ModuleNotFoundError: No module named 'backend'`**
You launched Streamlit from the wrong directory. Run
`streamlit run frontend/app.py` from the `bubbles/` project root.

**Weather / stock tool always returns an error**
Those two tools require `WEATHER_API_KEY` / `ALPHA_VANTAGE_API_KEY` in
`.env`. If you don't need them, this is expected and harmless — the rest
of the app works fine without them.

**Titles never show up / stay as "New chat (xxxxxxxx)"**
A title is only generated after the *first AI reply* in a thread. If a
thread has no messages yet (e.g. you clicked "New Chat" but haven't typed
anything), it won't have a title yet — that's expected.

**Port already in use (`5442` or `8501`)**
Something else on your machine is using that port. Either stop that
process, or change the port mapping in `docker-compose.yml` (and update
`POSTGRES_URI` to match) / pass `--server.port` to `streamlit run`.

**I want to wipe everything and start fresh**
`docker compose down -v` deletes the Postgres volume entirely (all short-
term and long-term memory, gone). Then `docker compose up -d` and
`python scripts/init_db.py` to recreate empty tables.

---

## Extending Bubbles

Some natural next steps, roughly in order of effort:

- **Semantic memory search** — swap the plain-text long-term memory store
  for one using `pgvector`, so `chat_node` can retrieve only the *most
  relevant* facts about a user instead of dumping all of them into the
  prompt every time (matters once a user has accumulated a lot of memory).
- **Real authentication** — replace the sidebar User ID text field with an
  actual login flow (e.g. Streamlit's built-in auth, or a reverse proxy
  with SSO), and derive `user_id` from the authenticated session.
- **Thread deletion / rename** — `backend/threads.py` already has
  `set_thread_title`; a delete/rename UI in the sidebar is a small
  addition on top of that.
- **Editable long-term memory** — a settings page that lists everything
  Bubbles has "remembered" about you and lets you delete individual facts
  (good practice for any app storing personal data).
- **Swap or add LLM providers** — `backend/llm.py` is the only place model
  instances are constructed, so adding an OpenAI/Anthropic fallback or
  swapping providers entirely is a localized change.

---

## What changed from the original prototype

Beyond the three headline asks (long-term memory, auto-titled threads,
production-style file split), a few latent issues from the original code
were fixed along the way:

- The hardcoded WeatherAPI key inside `get_weather` is now read from
  `WEATHER_API_KEY` instead of being committed in source.
- `generate_thread_id()` now returns a plain `str(uuid4())` instead of a
  `uuid.UUID` object — the original mixed UUID objects (in session state)
  with whatever type the checkpointer returns from
  `configurable.thread_id`, which could silently break thread
  deduplication/matching.
- Sidebar thread buttons now use an explicit, unique `key=` per thread,
  since two threads can now share a display label (their generated title)
  before Streamlit would otherwise raise a duplicate-widget-ID error.
- The SQLite checkpointer was swapped for a Postgres one, so short-term and
  long-term memory share one database and one connection pool instead of
  two separate storage engines.