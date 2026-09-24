# 💬 Bubbles

### A chatbot that remembers.

Bubbles is a conversational AI assistant built with **LangGraph, Groq, Streamlit, and PostgreSQL**.

Unlike a basic chatbot, Bubbles can remember things about you across conversations, use tools when needed, and keep your conversations organized.

> 💬 **Chat with it. Come back later. It remembers.**

---

## ✨ What can Bubbles do?

### 💬 Have normal conversations

Ask questions, have a conversation, or use it like a regular AI assistant.

Bubbles uses a Groq-hosted language model to generate its responses.

### 🧠 Remember your conversations

Bubbles remembers what was said inside each conversation.

So if you leave a chat and come back later, the conversation is still there.

### 💾 Remember useful things about you

Bubbles can also remember information that should survive across different chats.

For example:

```text
You:
I'm building a RAG application with LangGraph.

Bubbles:
Got it.

       ↓

You start a new conversation

       ↓

You:
What project was I working on?

Bubbles:
You were working on a RAG application with LangGraph.
```

This is handled separately from normal conversation history.

### 🛠️ Use tools

Bubbles can decide when a tool would be useful.

Currently, it can work with:

* 🔍 Web search
* 🧮 Calculator
* 🌤️ Weather
* 📈 Stock prices

You don't have to manually select a tool. The AI can decide when one is needed.

### 🏷️ Automatically name conversations

New conversations receive short titles automatically.

Instead of seeing:

```text
Chat 1
Chat 2
Chat 3
```

you might see:

```text
Understanding RAG
LangGraph Memory
Python Decorators
Building AI Agents
```

---

# 🧠 How Bubbles remembers

Bubbles uses two kinds of memory.

### 🟦 Short-term memory

This is the memory of **one conversation**.

It contains things like:

```text
Your messages
↓
AI responses
↓
Tool calls
↓
Tool results
```

It is tied to a `thread_id`.

Start a new conversation, and you get a new thread.

---

### 🟩 Long-term memory

This is information Bubbles can keep **across conversations**.

For example:

```text
User is learning LangGraph.
User is building a RAG application.
User prefers Python.
```

This memory is tied to a `user_id`, so it can be available when you start a completely new chat.

---

# 🏗️ How it works

You don't need to understand LangGraph to use Bubbles, but the basic idea is:

```text
                 👤 You
                   │
                   ▼
             🎨 Streamlit
                   │
                   ▼
              🔗 LangGraph
                   │
          ┌────────┴────────┐
          ▼                 ▼
     🧠 Memory          💬 Chat
                              │
                         Need a tool?
                         /          \
                       Yes           No
                        │             │
                        ▼             ▼
                   🛠️ Tool      ✨ Response
                        │
                        └──────► 💬 Chat
                                  │
                                  ▼
                            🗃️ PostgreSQL
```

PostgreSQL stores the information needed to bring conversations and long-term memory back later.

---

# 🛠️ Tech Stack

| Part                 | Technology     |
| -------------------- | -------------- |
| 🎨 Interface         | Streamlit      |
| 🤖 AI Model          | Groq           |
| 🔗 AI Workflow       | LangGraph      |
| 🗃️ Database         | PostgreSQL     |
| 🧠 Short-term memory | PostgresSaver  |
| 💾 Long-term memory  | PostgresStore  |
| 🐳 Database setup    | Docker Compose |
| 📦 Structured data   | Pydantic       |

---

# 🚀 Getting Started

## 1. Clone the project

```bash
git clone https://github.com/<your-username>/Bubbles.git
cd Bubbles
```

## 2. Start PostgreSQL

The easiest way is Docker:

```bash
docker compose up -d
```

---

## 3. Create a Python environment

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

## 4. Install the dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Add your API key

Create a `.env` file using `.env.example` as a starting point.

At minimum, you need:

```env
GROQ_API_KEY=your-groq-api-key
```

Optional tools require their own API keys:

```env
WEATHER_API_KEY=your-weather-api-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
```

> 🔐 Never upload your real `.env` file or API keys to GitHub.

---

## 6. Initialize the database

Run:

```bash
python scripts/init_db.py
```

---

## 7. Start Bubbles

```bash
streamlit run frontend/app.py
```

Then open the local address shown by Streamlit, usually:

```text
http://localhost:8501
```

That's it. 🎉

---

# 💬 Using Bubbles

### Start a conversation

Open the app and start chatting normally.

### Create another conversation

Click:

```text
➕ New Chat
```

Your new conversation gets its own short-term memory.

Your long-term memory, however, can still be available.

### Continue an old conversation

Choose one of your previous conversations from the sidebar.

Bubbles loads the conversation history from PostgreSQL.

### Try a tool

You can simply ask:

```text
What's the weather in Kolkata?
```

or:

```text
Calculate 125 * 48.
```

or:

```text
Search for the latest LangGraph release.
```

Bubbles can decide whether it needs a tool.

### Test long-term memory

Tell Bubbles:

```text
I'm building a RAG application using LangGraph.
```

Then create a new chat and ask:

```text
What project am I building?
```

If the memory was stored successfully, Bubbles can use that information in the new conversation.

---

# 📁 Project Structure

The project is organized into a few simple areas:

```text
Bubbles/
│
├── backend/
│   ├── config.py       # Configuration
│   ├── db.py           # PostgreSQL
│   ├── llm.py          # AI models
│   ├── memory.py       # Long-term memory
│   ├── nodes.py        # Chat logic
│   ├── prompts.py      # Prompts
│   ├── state.py        # Graph state
│   ├── threads.py      # Conversations
│   └── graph.py        # LangGraph workflow
│
├── frontend/
│   └── app.py          # Streamlit interface
│
├── scripts/
│   └── init_db.py      # Database setup
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

The main idea is to keep the **interface, AI logic, memory, tools, and database work separate**.

---

# 🔐 A note about users and memory

Bubbles uses a `user_id` to separate long-term memories.

For example:

```text
User A
 ├── Conversation 1
 ├── Conversation 2
 └── Long-term memory

User B
 ├── Conversation 1
 ├── Conversation 2
 └── Long-term memory
```

This means different users can have their own conversations and memories.

Currently, the project uses a User ID field in the interface rather than a full login system.

---

# 🛡️ What happens when something goes wrong?

Bubbles tries to keep optional features from breaking the entire chat.

For example, if the weather API isn't configured, the weather tool can return an error instead of bringing down the chatbot.

The same idea applies to long-term memory.

If memory extraction fails, the normal conversation can continue.

---

# 🔮 What's next?

Some ideas for future versions include:

* [ ] 🧠 Smarter semantic memory with `pgvector`
* [ ] 🔐 Proper user authentication
* [ ] ✏️ Rename conversations
* [ ] 🗑️ Delete conversations
* [ ] 🧠 View and edit saved memories
* [ ] 🧪 More automated tests
* [ ] 📊 Better monitoring
* [ ] 🔄 Support for more AI providers
* [ ] 🚀 Production deployment

---

# 🌱 Why I built Bubbles

Bubbles started as a small chatbot project and gradually grew into an exploration of how a more persistent AI assistant could work.

The main things I wanted to experiment with were:

**Conversation memory • Long-term memory • Tool calling • LangGraph • PostgreSQL • LLM orchestration**

Instead of treating every conversation as completely new, Bubbles explores what happens when an AI assistant can **remember, organize, and build context over time.**

---

# 🧈 Bubbles in one line

> **A conversational AI assistant that remembers your conversations, keeps useful information across chats, and knows when to use tools.**

---

## 👨‍💻 Author

**Sourasish Das**

Built while exploring:

**Generative AI • LangGraph • LLMs • Memory Systems • PostgreSQL • Streamlit**

---

<p align="center">

💬 **Talk to Bubbles.**
🧠 *It remembers.*

</p>
