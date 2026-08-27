# Skill: Total Calories for the Day

## Purpose

Use this skill when the user asks how many calories (or macros) they have
consumed — for today or a specific past day. This skill only **reports** totals;
it does not log new food. If the user is telling you what they ate, that belongs
to the `/add_calories` skill instead.

## Workflow — daily totals

1. Call `get_daily_totals_tool` to fetch the user's summed calories and macros.
2. Report the totals from the tool result: calories, protein, carbs, fat, and
   the number of entries.

## Rules

- Do NOT provide a `created_by` value; user identity is attached automatically.
- This skill never logs food. If the user names a food and an amount, tell them
  to use `/add_calories` to log it — do not attempt to add it here.
- Report only the numbers returned by `get_daily_totals_tool`. Never invent or
  estimate totals, and never fabricate the result of a tool call.
- If the day has no entries, the totals come back as zeros — say plainly that
  nothing has been logged for that day rather than inventing figures.
