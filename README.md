# 💬 Bubbles — Memory-Enabled LangGraph Chatbot

<p align="center">
  <b>🧠 A conversational AI assistant with short-term memory, long-term memory, tool calling, and ChatGPT-style conversation titles.</b>
</p>

<p align="center">
  <i>
    Built with LangGraph, Groq, Streamlit, and PostgreSQL.
  </i>
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange)
![Groq](https://img.shields.io/badge/Groq-LLM-black)
![Postgres](https://img.shields.io/badge/PostgreSQL-Memory-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)

</p>

---

## 📌 Overview

**Bubbles** is a LangGraph-powered conversational AI assistant designed around persistent memory.

It combines:

- 🧠 **Short-term memory** for conversation history
- 💾 **Long-term memory** for durable user facts
- 🛠️ **Tool calling** for external capabilities
- 🏷️ **Automatic conversation titles**
- 🗃️ **PostgreSQL-backed persistence**
- ⚡ **Streaming responses**
- 🎨 **Streamlit interface**

The project started as a small two-file prototype and was later rebuilt into a modular, production-style architecture.

### From Prototype → Bubbles

```text
Original Prototype
       │
       ├── UI
       ├── Graph
       ├── Prompts
       ├── Tools
       └── Memory
             │
             ▼
      Modular Architecture
             │
             ▼
        🧠 Bubbles
````

---

# ✨ What It Does

## 💬 Conversational Chat

Bubbles answers normal questions using a Groq-hosted LLM.

When additional information or computation is useful, the model can automatically call tools.

---

## 🧠 Short-Term Memory

Bubbles remembers the complete history of an individual conversation.

For example:

```text
User:
I'm learning LangGraph.

Assistant:
Nice! What are you building?

User:
I'm building a chatbot.

Assistant:
Since you're building a chatbot with LangGraph...
```

Conversation history is persisted in PostgreSQL, allowing users to leave a conversation and return to it later.

---

## 💾 Long-Term Memory

Bubbles can remember durable facts about a user across different conversations.

For example:

```text
Chat 1:
"I'm building a RAG application."

        ↓

Long-Term Memory

"User is building a RAG application."

        ↓

Chat 2:

"What should I work on next?"

Assistant can use the stored fact as context.
```

Long-term memory is associated with a **`user_id`**, rather than a conversation thread.

This means the memory survives when the user starts a new chat.

---

## 🛠️ Tool Calling

The chatbot can decide when to call external tools.

Currently supported tools include:

| Tool           | Purpose                                         |
| -------------- | ----------------------------------------------- |
| 🔍 Search      | DuckDuckGo web search                           |
| 🧮 Calculator  | Addition, subtraction, multiplication, division |
| 🌤️ Weather    | WeatherAPI.com                                  |
| 📈 Stock Price | Alpha Vantage                                   |

The LLM decides when a tool is useful instead of requiring the user to manually select one.

---

## 🏷️ Automatic Conversation Titles

Every conversation receives a ChatGPT-style title after its first exchange.

For example:

```text
💬 Conversations

Understanding RAG
LangGraph Memory
Python Decorators
Postgres Setup
Building AI Agents
```

Each thread receives only **one title-generation LLM call**.

Existing titles are reused without additional LLM calls.

---

# 🏗️ Architecture at a Glance

```text
┌──────────────────────┐
│      🎨 Streamlit    │
│       Frontend       │
│    frontend/app.py   │
└──────────┬───────────┘
           │
           │ Graph Invocation
           ▼
┌─────────────────────────────────────────────┐
│                 🔗 LangGraph                │
│                                             │
│                  START                      │
│                    │                        │
│                    ▼                        │
│              ┌───────────┐                  │
│              │ 🧠 remember│                  │
│              └─────┬─────┘                  │
│                    │                        │
│                    ▼                        │
│              ┌───────────┐                  │
│              │ 💬 chat_node│                 │
│              └─────┬─────┘                  │
│                    │                        │
│              Tool requested?                │
│                │         │                  │
│               YES        NO                 │
│                │         │                  │
│                ▼         ▼                  │
│          ┌──────────┐   END                 │
│          │ 🛠️ tools │                       │
│          └────┬─────┘                       │
│               │                             │
│               └────────► chat_node          │
│                                             │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
        ┌──────────────────────────────┐
        │       🗃️ PostgreSQL          │
        │                              │
        │  ┌────────────────────────┐  │
        │  │ 🧵 PostgresSaver       │  │
        │  │ Short-Term Memory      │  │
        │  │                        │  │
        │  │ Full thread history    │  │
        │  └────────────────────────┘  │
        │                              │
        │  ┌────────────────────────┐  │
        │  │ 💾 PostgresStore        │  │
        │  │ Long-Term Memory       │  │
        │  │                        │  │
        │  │ User facts             │  │
        │  │ Thread titles          │  │
        │  └────────────────────────┘  │
        │                              │
        └──────────────────────────────┘
```

---

# 🔄 Request Flow

Every user message passes through the LangGraph workflow once.

```text
👤 User Message
       │
       ▼
🧠 remember_node
       │
       │ Extract durable facts
       ▼
💬 chat_node
       │
       │ Read long-term memory
       │ Build personalized prompt
       │ Call LLM
       ▼
🤔 Tool required?
       │
   ┌───┴───┐
   │       │
  YES      NO
   │       │
   ▼       ▼
🛠️ Tool   ✨ Final Answer
   │
   ▼
💬 chat_node
   │
   └──────► repeat if another tool call is required
```

---

# 🧠 How Memory Works

Bubbles deliberately separates memory into **two different systems**.

```text
                  🧠 BUBBLES MEMORY
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      🟦 SHORT-TERM             🟩 LONG-TERM
         MEMORY                    MEMORY
             │                       │
      PostgresSaver             PostgresStore
             │                       │
        thread_id                user_id
             │                       │
     One conversation          All conversations
             │                       │
     Full message history      Durable user facts
```

---

## 🟦 Short-Term Memory — STM

Short-term memory answers:

> **"What was said in this conversation?"**

Implemented using:

```text
PostgresSaver
```

### Scope

```text
One thread
   │
   ├── Human messages
   ├── AI messages
   ├── Tool calls
   └── Tool results
```

### Key

```text
thread_id
```

Each conversation has its own independent history.

Starting a new chat creates a new thread, so the new conversation starts with empty short-term memory.

---

## 🟩 Long-Term Memory — LTM

Long-term memory answers:

> **"What do I know about this user?"**

Implemented using:

```text
PostgresStore
```

### Scope

```text
user_id
   │
   ├── Personal facts
   ├── Preferences
   ├── Projects
   └── Other durable information
```

For example:

```text
"User is building a RAG chatbot with LangGraph."
```

This information can be available across multiple conversation threads.

---

# 🔍 Memory Extraction

Long-term memory is not written blindly.

Every user turn passes through:

```text
User Message
     │
     ▼
🧠 remember_node
     │
     ▼
Memory Extraction LLM
     │
     ▼
Structured MemoryDecision
     │
     ├── No new facts
     │
     └── New facts
            │
            ▼
       PostgresStore
```

The memory LLM determines:

* Whether something is worth remembering
* Which facts are genuinely new
* Which existing facts should not be duplicated

Structured output is represented using Pydantic models such as:

```python
MemoryItem
MemoryDecision
```

---

## 🛡️ Fail-Safe Memory

Memory extraction is intentionally isolated from the main chat response.

If the memory LLM fails:

```text
Memory Error
     │
     ▼
remember_node → {}
     │
     ▼
chat_node continues normally
```

So a memory extraction failure doesn't break the user's actual conversation.

---

# 🏷️ How Thread Titles Work

Thread titles are stored in PostgreSQL using a separate namespace:

```text
("thread_titles",)
```

The process is:

```text
First User Message
        │
        ▼
First AI Response
        │
        ▼
Check Existing Title
        │
    ┌───┴───┐
    │       │
   YES      NO
    │       │
    ▼       ▼
 Return   🧠 Title LLM
 Existing     │
              ▼
          Sanitize Title
              │
              ▼
         Save to Store
              │
              ▼
         Return Title
```

### Important

A thread receives **only one title-generation LLM call**.

After a title exists:

```text
get_thread_title()
        │
        ▼
Existing title
        │
        ▼
No additional LLM call
```

This keeps the feature simple and avoids unnecessary API usage.

---

# 🗃️ Project Structure

```text
bubbles/
│
├── 🐳 docker-compose.yml
├── 📦 requirements.txt
├── 🔐 .env.example
├── 📄 README.md
│
├── 📁 scripts/
│   └── init_db.py
│
├── 📁 backend/
│   │
│   ├── __init__.py
│   │
│   ├── ⚙️ config.py
│   │   └── Environment variables and configuration
│   │
│   ├── 🗃️ db.py
│   │   └── PostgreSQL connection pool + memory factories
│   │
│   ├── 🤖 llm.py
│   │   └── Chat, memory, and title LLM instances
│   │
│   ├── 🛠️ tools.py
│   │   └── Search, weather, stock, calculator
│   │
│   ├── 📦 state.py
│   │   └── ChatState definition
│   │
│   ├── 📝 prompts.py
│   │   └── Centralized prompt templates
│   │
│   ├── 🧠 memory.py
│   │   └── Long-term memory extraction + retrieval
│   │
│   ├── 🔗 nodes.py
│   │   └── Chat node + tool node
│   │
│   ├── 🏷️ threads.py
│   │   └── Thread listing + title generation
│   │
│   └── 🔄 graph.py
│       └── LangGraph workflow assembly
│
└── 📁 frontend/
    └── 🎨 app.py
        └── Streamlit user interface
```

---

# 📚 File-by-File Reference

## ⚙️ `backend/config.py`

The centralized configuration layer.

It is the only module responsible for reading environment variables.

Examples include:

```text
GROQ_API_KEY
GROQ_MODEL
POSTGRES_URI
MAX_TITLE_WORDS
WEATHER_API_KEY
ALPHA_VANTAGE_API_KEY
```

This keeps configuration and secrets centralized.

---

## 🗃️ `backend/db.py`

Responsible for the PostgreSQL connection pool and memory infrastructure.

Provides:

```text
get_checkpointer()
get_store()
init_db()
```

The same PostgreSQL instance is used for both short-term and long-term memory.

---

## 🤖 `backend/llm.py`

Creates the three LLM instances used by the application:

```text
chat_llm
memory_llm
title_llm
```

### Chat LLM

Used for normal conversations and tool calling.

```text
temperature = 0.4
```

### Memory LLM

Used for deterministic fact extraction.

```text
temperature = 0
```

### Title LLM

Used for deterministic conversation naming.

```text
temperature = 0
```

---

## 🛠️ `backend/tools.py`

Contains all model-callable tools.

### 🔍 Search

DuckDuckGo web search.

### 🧮 Calculator

Supports:

```text
+
-
*
/
```

Input values are converted to `float` because LLMs may provide numbers as strings.

### 🌤️ Weather

Uses WeatherAPI.com.

Requires:

```text
WEATHER_API_KEY
```

### 📈 Stock Price

Uses Alpha Vantage.

Requires:

```text
ALPHA_VANTAGE_API_KEY
```

API-dependent tools return a structured error instead of crashing when a required key isn't configured.

---

## 📦 `backend/state.py`

Defines the graph state:

```python
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

`add_messages` ensures new messages are appended rather than replacing the existing history.

---

## 📝 `backend/prompts.py`

Centralizes all prompts:

```text
SYSTEM_PROMPT_TEMPLATE
MEMORY_EXTRACTION_PROMPT
TITLE_GENERATION_PROMPT
```

Keeping prompts separate from application logic makes them easier to modify and evaluate.

---

## 🧠 `backend/memory.py`

Responsible for long-term memory.

Main responsibilities:

```text
MemoryItem
MemoryDecision
get_user_details()
remember_node()
```

The memory node:

1. Reads the latest human message.
2. Reads existing user memory.
3. Sends both to the memory LLM.
4. Receives structured output.
5. Stores only genuinely new facts.

---

## 🔗 `backend/nodes.py`

Contains the main LangGraph nodes.

The chat model is bound to the available tools:

```python
llm_with_tools = chat_llm.bind_tools(TOOLS)
```

`chat_node()`:

* Reads conversation history
* Reads long-term user memory
* Builds the system prompt
* Invokes the LLM
* Returns the response

`tool_node` uses LangGraph's prebuilt `ToolNode`.

---

## 🏷️ `backend/threads.py`

Handles:

* Thread listing
* Thread IDs
* Thread titles
* Title generation
* Title retrieval

It also provides:

```text
retrieve_all_thread_ids()
```

which scans the checkpointer for known conversation threads.

---

## 🔄 `backend/graph.py`

The central LangGraph assembly point.

The workflow is conceptually:

```python
graph.add_edge(START, "remember")
graph.add_edge("remember", "chat_node")

graph.add_conditional_edges(
    "chat_node",
    tools_condition
)

graph.add_edge("tools", "chat_node")
```

The compiled graph is exported for use by the frontend.

---

## 🎨 `frontend/app.py`

The Streamlit interface provides:

* 👤 User ID input
* ➕ New Chat
* 💬 Chat interface
* 📚 Previous conversations
* 🏷️ Automatic titles
* ⚡ Streaming responses

The frontend invokes the compiled LangGraph workflow instead of containing the chatbot logic itself.

---

# 🛠️ Tech Stack

| Layer                | Technology              |
| -------------------- | ----------------------- |
| 🎨 Frontend          | Streamlit               |
| 🤖 LLM               | Groq + `langchain-groq` |
| 🔗 Orchestration     | LangGraph               |
| 🗃️ Database         | PostgreSQL              |
| 🧠 Short-Term Memory | `PostgresSaver`         |
| 💾 Long-Term Memory  | `PostgresStore`         |
| 🐳 Database Runtime  | Docker Compose          |
| 📦 Structured Output | Pydantic                |
| 🔍 Web Search        | DuckDuckGo              |
| 🌤️ Weather          | WeatherAPI.com          |
| 📈 Stock Data        | Alpha Vantage           |

---

# 📋 Requirements

You need:

* 🐍 Python **3.11+**
* 🐳 Docker
* 🗃️ PostgreSQL 14+ if using an external database
* 🔑 Groq API key

### Optional

These are only required if you want the corresponding tools:

* 🌤️ WeatherAPI.com API key
* 📈 Alpha Vantage API key

---

# 🚀 Setup

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/<your-username>/Bubbles.git
cd Bubbles
```

---

## 2️⃣ Start PostgreSQL

Using Docker Compose:

```bash
docker compose up -d
```

For older Docker installations:

```bash
docker-compose up -d
```

---

## 3️⃣ Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

---

## 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5️⃣ Configure Environment Variables

Copy:

```bash
cp .env.example .env
```

Then edit `.env`.

At minimum:

```env
GROQ_API_KEY=your-groq-api-key
```

---

## 6️⃣ Initialize the Database

Run:

```bash
python scripts/init_db.py
```

This creates the required PostgreSQL tables.

---

## 7️⃣ Run Bubbles

```bash
streamlit run frontend/app.py
```

Streamlit will provide a local URL, usually:

```text
http://localhost:8501
```

---

# 🔐 Environment Variables

| Variable                | Required? | Default                                     | Purpose                 |
| ----------------------- | --------- | ------------------------------------------- | ----------------------- |
| `GROQ_API_KEY`          | ✅ Yes     | —                                           | Authentication for Groq |
| `GROQ_MODEL`            | ❌ No      | `meta-llama/llama-4-scout-17b-16e-instruct` | Groq model              |
| `POSTGRES_URI`          | ❌ No      | Local Docker PostgreSQL                     | Database connection     |
| `WEATHER_API_KEY`       | ❌ No      | —                                           | Weather tool            |
| `ALPHA_VANTAGE_API_KEY` | ❌ No      | —                                           | Stock price tool        |
| `MAX_TITLE_WORDS`       | ❌ No      | `6`                                         | Maximum title length    |

> ⚠️ Never commit `.env` or real API keys to GitHub.

---

# ▶️ Running the App

Run from the project root:

```bash
streamlit run frontend/app.py
```

### Start PostgreSQL

```bash
docker compose up -d
```

### Stop PostgreSQL

```bash
docker compose down
```

### Delete all database data

⚠️ This permanently removes stored conversations and long-term memory:

```bash
docker compose down -v
```

---

# 💻 Using Bubbles

### 1️⃣ Set a User ID

The sidebar contains a User ID field.

For example:

```text
default_user
```

The User ID determines which long-term memory belongs to the current user.

---

### 2️⃣ Start a New Chat

Click:

```text
➕ New Chat
```

This creates a new thread.

Short-term memory starts fresh, but long-term memory remains available.

---

### 3️⃣ Continue Previous Conversations

Select a conversation from the sidebar.

The complete thread history is restored from PostgreSQL.

---

### 4️⃣ Use Tools Naturally

Ask something like:

```text
What's the weather in Kolkata?
```

or:

```text
Search for the latest LangGraph release.
```

or:

```text
Calculate 125 * 48.
```

The model can decide whether a tool is necessary.

---

### 5️⃣ Test Long-Term Memory

Tell Bubbles:

```text
I'm building a RAG application using LangGraph.
```

Then click:

```text
➕ New Chat
```

Ask:

```text
What project am I building?
```

The assistant can retrieve the stored user fact from long-term memory.

---

# 👥 Multi-User Design

The prototype originally had no concept of users.

Bubbles introduces:

```text
user_id
```

as the identity key for long-term memory.

The architecture becomes:

```text
                👤 User
                  │
             user_id = A
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   Thread A1             Thread A2
        │                   │
        └─────────┬─────────┘
                  ▼
          🧠 Shared LTM
```

Different users can therefore have independent long-term memories.

For a real deployment, the sidebar User ID could be replaced with an authentication system.

The backend architecture already passes `user_id` through the graph configuration.

---

# 🛡️ Error Handling

Bubbles is designed to degrade gracefully.

### Missing Weather API Key

```text
get_weather()
      │
      ▼
No API key
      │
      ▼
{"error": "..."}
```

The application continues running.

### Missing Stock API Key

The stock tool similarly returns a clear error rather than crashing the conversation.

### Memory Extraction Failure

```text
Memory LLM fails
      │
      ▼
remember_node → {}
      │
      ▼
Normal chat continues
```

This keeps long-term memory from becoming a single point of failure for the chatbot.

---

# 🐛 Troubleshooting

## ❌ PostgreSQL Connection Refused

Make sure PostgreSQL is running:

```bash
docker ps
```

Then verify:

```text
POSTGRES_URI
```

matches the port configured in:

```text
docker-compose.yml
```

The default project configuration uses:

```text
5442
```

rather than PostgreSQL's usual `5432`.

---

## ❌ `ModuleNotFoundError: No module named 'backend'`

Make sure you're running Streamlit from the project root:

```bash
cd bubbles
streamlit run frontend/app.py
```

---

## ❌ Weather or Stock Tool Returns an Error

Add the required API key to `.env`:

```env
WEATHER_API_KEY=your-key
```

or:

```env
ALPHA_VANTAGE_API_KEY=your-key
```

---

## ❌ Conversation Title Not Showing

A title is generated only after the first AI response.

A newly created empty thread will therefore display something similar to:

```text
New chat (1a2b3c4d)
```

until the first conversation exchange occurs.

---

## ❌ Port Already in Use

If port `5442` or `8501` is already occupied:

* Stop the process using the port, or
* Change the PostgreSQL port mapping
* Update `POSTGRES_URI` accordingly

For Streamlit, you can also use:

```bash
streamlit run frontend/app.py --server.port 8502
```

---

# 🔮 Extending Bubbles

## 🧠 Semantic Long-Term Memory

Currently, long-term memory consists of stored facts.

A future implementation could use:

```text
PostgreSQL
    │
    └── pgvector
          │
          ▼
   Semantic Memory Search
```

This would allow the assistant to retrieve only the most relevant memories rather than injecting every stored fact into the prompt.

---

## 🔐 Real Authentication

Replace the User ID text field with an actual authentication system.

For example:

```text
Login
  │
  ▼
Authenticated User
  │
  ▼
user_id
  │
  ▼
LangGraph
```

The underlying memory architecture can remain largely unchanged.

---

## ✏️ Thread Rename / Delete

Add sidebar controls for:

```text
✏️ Rename
🗑️ Delete
```

The existing thread abstraction provides a natural place for these operations.

---

## 🧠 Editable Memory

A useful future feature would be a memory settings page:

```text
┌──────────────────────────────┐
│ 🧠 What Bubbles Remembers    │
├──────────────────────────────┤
│ • Building a RAG application  │ 🗑️
│ • Uses LangGraph              │ 🗑️
│ • Learning Python             │ 🗑️
└──────────────────────────────┘
```

Users could inspect and delete individual memories.

---

## 🔄 Multiple LLM Providers

Because model initialization is centralized in:

```text
backend/llm.py
```

additional providers could be introduced without changing the entire application architecture.

Possible future providers include:

```text
Groq
OpenAI
Anthropic
Local Models
```

---

# 🔧 What Changed From the Original Prototype

Bubbles evolved significantly from the original two-file implementation.

### 🏗️ Modular Architecture

**Before:**

```text
6.app_tools.py
chatbot_backend_tools_6.py
```

**After:**

```text
backend/
frontend/
scripts/
```

Responsibilities are now separated into dedicated modules.

---

### 💾 Long-Term Memory

Added:

```text
PostgresStore
```

for persistent user-level facts.

---

### 🧵 Persistent Short-Term Memory

The original SQLite-based checkpointer was replaced with:

```text
PostgresSaver
```

so conversation history is persisted in PostgreSQL.

---

### 🏷️ Automatic Thread Titles

Added an LLM-powered title-generation system.

Each thread gets one generated title.

---

### 🔐 Secret Management

Hardcoded API credentials were removed.

Secrets are now loaded from:

```text
.env
```

---

### 🆔 Thread ID Handling

Thread IDs are normalized to plain strings instead of mixing UUID objects with string values.

This avoids potential thread matching and deduplication problems.

---

### 🎨 Streamlit Improvements

Thread buttons use explicit unique widget keys so multiple conversations with identical generated titles don't cause duplicate Streamlit widget IDs.

---

# 📊 Architecture Principles

Bubbles follows a few important design principles:

### 1. 🧩 Separation of Concerns

```text
Frontend
   │
   ▼
Graph
   │
   ├── Nodes
   ├── Memory
   ├── Tools
   └── LLM
```

Each component has a focused responsibility.

---

### 2. 🧠 Memory Separation

```text
STM → Thread-specific
LTM → User-specific
```

This distinction makes the memory system easier to reason about and extend.

---

### 3. 🔐 Centralized Configuration

Environment variables are read in one place:

```text
backend/config.py
```

---

### 4. 🛡️ Graceful Failure

Optional services should fail without taking down the entire chatbot.

```text
Optional Tool Failure
        ↓
Clear Error
        ↓
Chat Continues
```

---

### 5. 🔄 Graph-Based Orchestration

LangGraph manages the control flow:

```text
START
  ↓
remember
  ↓
chat
  ↓
tools? ── YES ──► tools
  │                 │
  │                 ▼
  └────────────── chat
  │
  NO
  ↓
END
```

---

# 🗺️ Roadmap

* [ ] 🧠 Semantic long-term memory with `pgvector`
* [ ] 🔐 Real authentication
* [ ] ✏️ Thread rename functionality
* [ ] 🗑️ Thread deletion
* [ ] 🧠 Editable memory management
* [ ] 🧪 Automated tests
* [ ] 📊 Memory and tool-call observability
* [ ] 🔄 Multi-provider LLM support
* [ ] 🚀 Production deployment

---

# ⭐ Why Bubbles?

Bubbles explores the architecture behind a more persistent AI assistant rather than a simple chatbot.

The core idea is:

```text
                 💬 Conversation
                        │
                        ▼
                 🔗 LangGraph
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      🧠 Memory      🛠️ Tools      🤖 LLM
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                  🗃️ PostgreSQL
                        │
                        ▼
                  ✨ AI Response
```

It demonstrates how **conversation state, persistent user memory, tool calling, and LLM orchestration** can work together in a single application.

---

# 🧈 Bubbles in One Line

> **A persistent LangGraph chatbot that remembers conversations, learns durable user facts, calls tools when needed, and organizes chats automatically.**

---

## 👨‍💻 Author

**Sourasish Das**

Built as an exploration of:

**Generative AI • LangGraph • LLM Tool Calling • Memory Systems • PostgreSQL • Streamlit**

---

<p align="center">
  💬 <b>Talk to Bubbles.</b>
  <br>
  🧠 <i>It remembers.</i>
</p>
