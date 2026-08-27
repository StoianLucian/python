# `/total_calories` Response Examples

These examples describe the **final response** returned to the user *after*
`get_daily_totals_tool` has run. They use only the base `text` and `error`
object types.

## Output Format

- Return a JSON array.
- Emit a single `text` object summarizing the day's totals: calories, protein,
  carbs, fat, and how many entries make up the total.
- Report only the numbers from the tool result. NEVER invent or estimate totals.
- If the day has no entries (all totals are `0`), say nothing has been logged for
  that day instead of reporting fake numbers (see Example 3).
- If a tool returned `success: false`, return a single `error` object.

---

## Example 1 – Today's totals

Tool result (`get_daily_totals_tool`):
```json
{ "success": true, "result": { "date": "2026-08-24", "calories": 508, "protein": 51.9, "carbs": 56, "fat": 6, "entries": 2 } }
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

## Example 2 – A specific past day

The user asks about a past date, so `get_daily_totals_tool` was called with
`day: "2026-08-20"`.

Tool result:
```json
{ "success": true, "result": { "date": "2026-08-20", "calories": 1840, "protein": 120, "carbs": 190, "fat": 55, "entries": 6 } }
```

Response:
```json
[
  {
    "type": "text",
    "text": "On 2026-08-20 you ate 1840 kcal across 6 items: 120g protein, 190g carbs, 55g fat."
  }
]
```

---

## Example 3 – Nothing logged

Tool result (no entries for the day):
```json
{ "success": true, "result": { "date": "2026-08-24", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "entries": 0 } }
```

Response:
```json
[
  {
    "type": "text",
    "text": "You haven't logged any food for today yet."
  }
]
```

---

## Example 4 – Tool failed

```json
[
  {
    "type": "error",
    "text": "Sorry, I couldn't fetch your totals. Please try again."
  }
]
```
