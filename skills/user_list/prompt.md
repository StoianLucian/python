# Skill: Users List

## Purpose

Use this skill whenever the user asks to retrieve, list, or view all available users.

Examples include:
- "Show me all users"
- "List all available users"
- "Who are the users?"
- "Get the full user list"
- "Return all users"

## Workflow

1. Retrieve the complete list of available users with the `get_all_users` tool.
2. Return all users available to the user.
3. Do not omit, invent, or modify users.
4. Emit one `user-mention` object per user, as shown in the skill examples.
5. If no users are available, clearly state that no users were found.
6. If the user-list data is incomplete or unavailable, explain that rather than guessing.

## Rules

- Always return the complete available user list when the user asks for all users.
- Preserve the user information as returned by the data source.
- Do not fabricate user details.
- Do not filter, rank, or summarize the list unless the user explicitly asks.
- Never format the users as prose, a numbered list, a table, or Markdown bullets.
  Each user is its own `user-mention` object.