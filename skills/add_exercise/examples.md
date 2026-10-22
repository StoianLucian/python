# Exercise — Response Format

Answer in **Markdown**, built only from the exercise tool results.

## Output Format

- Confirm each exercise that was logged — the exercise, the amount (reps or
  minutes), and the calories burned for that amount.
- Report the computed calories from the tool result, never the per-rep /
  per-minute rate or the arguments you passed in.
- After logging, end with the user's total calories burned today, from
  `today_total_calories_burned` in the last `add_exercise_entry` result (state it
  once, using the last result, even when several exercises were logged).
- Only confirm exercises that appear in an `add_exercise_entry` tool result.
  NEVER invent an exercise, its amount, or its calories.
- If no `add_exercise_entry` result is present (e.g. no amount was given), do NOT
  claim anything was logged — ask for the reps or minutes instead.
- If a tool returned `success: false`, briefly say you couldn't log it.

---

## Example 1 — One rep-based exercise logged

Tool result (`add_exercise_entry`):
```json
{ "success": true, "result": { "name": "push-ups", "type": "reps", "reps": 20, "category": "chest", "calories_burned": 6, "today_total_calories_burned": 6 } }
```

Response:
```markdown
Logged **20 push-ups** (chest): **6 kcal** burned.

Burned today: **6 kcal**.
```

---

## Example 2 — One duration-based exercise logged

Tool result (`add_exercise_entry`):
```json
{ "success": true, "result": { "name": "running", "type": "duration", "minutes": 10, "category": "cardio", "calories_burned": 100, "today_total_calories_burned": 106 } }
```

Response:
```markdown
Logged **10 minutes of running** (cardio): **100 kcal** burned.

Burned today: **106 kcal**.
```

---

## Example 3 — Missing amount (no tool called)

```markdown
How many push-ups did you do?
```

---

## Example 4 — Daily totals

Tool result (`get_exercise_daily_totals`):
```json
{ "success": true, "result": { "date": "2026-09-08", "calories": 106, "entries": 2 } }
```

Response:
```markdown
Today you've burned **106 kcal** across 2 exercises.
```

---

## Example 5 — Tool failed

```markdown
Sorry, I couldn't log that exercise. Please try again.
```
