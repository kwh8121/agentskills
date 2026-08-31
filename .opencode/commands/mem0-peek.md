---
description: Searches memories and displays compact one-liner results, or looks up a specific memory by ID. Use for quick memory lookups, checking if a decision was recorded, resolving [mem0:id] citations, or browsing memories without full category detail.
---
Load and follow the skill at .opencode/skills/mem0-peek/SKILL.md

Use the mem0 MCP tools (search_memories, get_memories, add_memory, delete_memory, update_memory, list_entities, delete_entities, get_event_status) to execute the skill instructions.

Identity context (from environment):
- user_id: Use MEM0_USER_ID env var, or fall back to $USER
- app_id: Use MEM0_APP_ID env var
- session_id: Use MEM0_SESSION_ID env var
- branch: Use MEM0_BRANCH env var
