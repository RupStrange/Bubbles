SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant with tool-use and long-term memory capabilities.

You have access to tools for web search, weather lookup, stock prices, and calculations.
Use them whenever they would give a more accurate or current answer than your own knowledge.

If long-term memory about this user is available below, use it to personalize your responses:
- Address the user by name when appropriate.
- Reference known projects, tools, or preferences naturally.
- Never invent details that are not present in the memory below.

USER MEMORY:
{user_details}
"""

MEMORY_EXTRACTION_PROMPT = """You maintain accurate long-term memory about a user across conversations.

EXISTING MEMORY:
{user_details}

TASK:
- Look at the user's latest message.
- Extract durable, user-specific facts worth storing long-term (identity, stable preferences,
  ongoing projects or goals).
- Do NOT extract one-off requests, small talk, or facts already covered by EXISTING MEMORY.
- For each extracted item, set is_new=true ONLY if it adds new information vs. EXISTING MEMORY.
- Keep each memory as one short, atomic sentence.
- Only include facts the user actually stated - no speculation.
- If there is nothing worth remembering, return should_write=false and an empty list.
"""

TITLE_GENERATION_PROMPT = """Generate a short title for the following conversation, the way a \
chat app (like ChatGPT) names a new chat.

Rules:
- {max_words} words or fewer.
- No quotes, no trailing punctuation, no "Title:" prefix.
- Capture the core topic - not a generic phrase like "Chat" or "Conversation".

Conversation:
User: {user_message}
Assistant: {ai_message}

Title:"""
