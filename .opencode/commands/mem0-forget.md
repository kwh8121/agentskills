---
description: Deletes memories by search query or memory ID with confirmation before removal. Use when removing outdated decisions, incorrect memories, sensitive data, or cleaning up after experiments. Also handles undo of recent additions.
---
Load and follow the skill at .opencode/skills/mem0-forget/SKILL.md

Use the mem0 MCP tools (search_memories, get_memories, add_memory, delete_memory, update_memory, list_entities, delete_entities, get_event_status) to execute the skill instructions.

Identity context (from environment):
- user_id: Use MEM0_USER_ID env var, or fall back to $USER
- app_id: Use MEM0_APP_ID env var
- session_id: Use MEM0_SESSION_ID env var
- branch: Use MEM0_BRANCH env var
