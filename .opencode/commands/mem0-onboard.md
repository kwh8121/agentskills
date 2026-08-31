---
description: Sets up mem0 for a new project including API key configuration, MCP authentication, project file import, and coding categories. Use on first run in a new project, when API key needs updating, or to re-run initial setup after configuration changes.
---
Load and follow the skill at .opencode/skills/mem0-onboard/SKILL.md

Use the mem0 MCP tools (search_memories, get_memories, add_memory, delete_memory, update_memory, list_entities, delete_entities, get_event_status) to execute the skill instructions.

Identity context (from environment):
- user_id: Use MEM0_USER_ID env var, or fall back to $USER
- app_id: Use MEM0_APP_ID env var
- session_id: Use MEM0_SESSION_ID env var
- branch: Use MEM0_BRANCH env var
