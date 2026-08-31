---
description: Overrides the auto-detected project scope to read and write memories under a different project ID, or enables global search to access all memories across all users and projects. Use when working across multiple projects, accessing memories from another repo, enabling team-wide memory access, or when auto-detection resolves to the wrong project.
---
Load and follow the skill at .opencode/skills/mem0-switch-project/SKILL.md

Use the mem0 MCP tools (search_memories, get_memories, add_memory, delete_memory, update_memory, list_entities, delete_entities, get_event_status) to execute the skill instructions.

Identity context (from environment):
- user_id: Use MEM0_USER_ID env var, or fall back to $USER
- app_id: Use MEM0_APP_ID env var
- session_id: Use MEM0_SESSION_ID env var
- branch: Use MEM0_BRANCH env var
