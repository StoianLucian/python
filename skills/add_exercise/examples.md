# `/add_exercise` Response Examples

These examples describe the **final response** returned to the user *after* the
exercise tools have run. They use only the base `text` and `error` object types.

## Output Format

- Return a JSON array.
- Emit one `text` object per exercise that was logged, confirming the exercise,
  the amount (reps or minutes), and the calories burned for that amount.
- When reporting daily totals, emit a single `text` object summarizing the day.
- Report the computed calories from the tool result, never the per-rep /
  per-minute rate or the arguments you passed in.
- After logging, add ONE final `text` object stating the user's total calories
  burned today, taken from `today_total_calories_burned` in the last
  `add_exercise_entry` result (e.g. "Burned today: 120 kcal."). When several
  exercises are logged in one message, emit this only once, using the last result.
- Only confirm exercises that appear in an `add_exercise_entry` tool result.
  NEVER invent an exercise, its amount, or its calories. Every number you state
  must come from a tool result.
- If no `add_exercise_entry` result is present (e.g. no tool was called because
  the user gave no amount), do NOT claim anything was logged — instead ask the
  user for the reps or minutes (see Example 3).
- If a tool returned `success: false`, return a single `error` object.

---

## Example 1 – One rep-based exercise logged

Tool result (`add_exercise_entry`):
```json
{ "success": true, "result": { "name": "push-ups", "type": "reps", "reps": 20, "minutes": null, "category": "chest", "calories_burned": 6, "today_total_calories_burned": 6 } }
```

Response:
```json
[
  {
    "type": "text",
    "text": "Logged 20 push-ups (chest): 6 kcal burned."
  },
  {
    "type": "text",
    "text": "Burned today: 6 kcal."
  }
]
```

---

## Example 2 – One duration-based exercise logged

Tool result (`add_exercise_entry`):
```json
{ "success": true, "result": { "name": "running", "type": "duration", "reps": null, "minutes": 10, "category": "cardio", "calories_burned": 100, "today_total_calories_burned": 106 } }
```

Response:
```json
[
  {
    "type": "text",
    "text": "Logged 10 minutes of running (cardio): 100 kcal burned."
  },
  {
    "type": "text",
    "text": "Burned today: 106 kcal."
  }
]
```

---

## Example 3 – Missing amount

When the user names an exercise but gives no reps/minutes, no tool was called —
ask for the amount:
```json
[
  {
    "type": "text",
    "text": "How many push-ups did you do?"
  }
]
```

---

## Example 4 – Daily totals

Tool result (`get_exercise_daily_totals`):
```json
{ "success": true, "result": { "date": "2026-09-08", "calories": 106, "entries": 2 } }
```

Response:
```json
[
  {
    "type": "text",
    "text": "Today you've burned 106 kcal across 2 exercises."
  }
]
```

---

## Example 5 – Tool failed

```json
[
  {
    "type": "error",
    "text": "Sorry, I couldn't log that exercise. Please try again."
  }
]
```
