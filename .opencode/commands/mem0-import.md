---
description: Imports memories from an exported Markdown file or MEMORY.md into the current project. Use when migrating from another project, restoring from backup, importing Claude Code native MEMORY.md content, or setting up a new project with existing knowledge.
---
Load and follow the skill at .opencode/skills/mem0-import/SKILL.md

Use the mem0 MCP tools (search_memories, get_memories, add_memory, delete_memory, update_memory, list_entities, delete_entities, get_event_status) to execute the skill instructions.

Identity context (from environment):
- user_id: Use MEM0_USER_ID env var, or fall back to $USER
- app_id: Use MEM0_APP_ID env var
- session_id: Use MEM0_SESSION_ID env var
- branch: Use MEM0_BRANCH env var
