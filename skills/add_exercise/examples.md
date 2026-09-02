# `/calories` Response Examples

These examples describe the **final response** returned to the user *after* the
calorie tools have run. They use only the base `text` and `error` object types.

## Output Format

- Return a JSON array.
- Emit one `text` object per exercise that was logged, confirming the exercise, the
  repetitions, and how many calories it consumes.
- When reporting daily totals, emit a single `text` object summarizing the day.
- Report the computed **totals** from the tool result, never the per-100g values
  or the arguments you passed in.
- After logging, add ONE final `text` object stating the user's total calories
  for today, taken from `today_total_calories` in the last `add_exercise_entry`
  result (e.g. "Today's total: 508 kcal."). When several foods are logged in one
  message, emit this only once, using the last result's value.
- Only confirm foods that appear in an `add_exercise_entry` tool result. NEVER invent
  a food, its grams, or its macros, and never say "Logged …" for a food that was
  not actually logged. Every number you state must come from a tool result.
- If no `add_exercise_entry` result is present (e.g. no tool was called because the
  user gave no gram amount), do NOT claim anything was logged — instead ask the
  user how many repetitons they made (see Example 4).
- If a tool returned `success: false`, return a single `error` object.

---

## Example 1 – One food logged

Tool result (`add_exercise_entry`):
```json
{ "success": true, "result": { "name": "pushup", "grams": 150, "category": "upper-body", "calories": 0.5} }
```

Response:
```json
[
  {
    "type": "text",
    "text": "Logged 150g of chicken breast (meat): 248 kcal, 46.5g protein, 0g carbs, 5.4g fat."
  },
  {
    "type": "text",
    "text": "Today's total: 508 kcal."
  }
]
```

---

## Example 2 – Multiple foods logged

Response:
```json
[
  {
    "type": "text",

  },
  {
    "type": "text",

  }
]
```

---

## Example 3 – Daily totals

Tool result (`get_daily_totals_tool`):
```json
{ "success": true, "result": { "date": "2009-08-15", "calories": 508, "protein": 51.9, "carbs": 56, "fat": 6, "entries": 2 } }
```

Response:
```json
[
  {
    "type": "text",
    "text": "Today you've eaten 508 kcal across 2 items: 51.9g protein, 56g carbs, 6g fat."
  }
]
```

---

## Example 4 – Missing or zero amount

When the user names a food but gives no grams (or `0` grams), no tool was
called — ask for the amount:
```json
[
  {
    "type": "text",
    "text": "How many grams of chicken did you eat?"
  }
]
```

---

## Example 5 – Tool failed

```json
[
  {
    "type": "error",
    "text": "Sorry, I couldn't log that food. Please try again."
  }
]
```
