---
description: Diagnoses mem0 connectivity, API key validity, and memory read/write functionality. Use when memory operations fail, searches return empty, add_memory errors occur, MCP connection drops, or to verify the plugin is working correctly.
---
Load and follow the skill at .opencode/skills/mem0-health/SKILL.md

Use the mem0 MCP tools (search_memories, get_memories, add_memory, delete_memory, update_memory, list_entities, delete_entities, get_event_status) to execute the skill instructions.

Identity context (from environment):
- user_id: Use MEM0_USER_ID env var, or fall back to $USER
- app_id: Use MEM0_APP_ID env var
- session_id: Use MEM0_SESSION_ID env var
- branch: Use MEM0_BRANCH env var
