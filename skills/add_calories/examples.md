# Calories — Response Format

Answer in **Markdown**, built only from the calorie tool results.

## Output Format

- Confirm each food that was logged — the food, the grams, and the computed
  totals (calories + macros) for that amount.
- Report the computed **totals** from the tool result, never the per-100g values
  or the arguments you passed in.
- After logging, end with the user's total calories for today, from
  `today_total_calories` in the last `add_food_entry` result (state it once,
  using the last result, even when several foods were logged).
- Only confirm foods that appear in an `add_food_entry` tool result. NEVER invent
  a food, its grams, or its macros, and never say "Logged …" for a food that was
  not actually logged.
- If no `add_food_entry` result is present (e.g. no grams were given), do NOT
  claim anything was logged — ask how many grams they ate instead.
- If a tool returned `success: false`, briefly say you couldn't log it.

---

## Example 1 — One food logged

Tool result (`add_food_entry`):
```json
{ "success": true, "result": { "name": "chicken breast", "grams": 150, "category": "meat", "calories": 247.5, "protein": 46.5, "carbs": 0, "fat": 5.4, "today_total_calories": 508 } }
```

Response:
```markdown
Logged **150g of chicken breast** (meat): **248 kcal**, 46.5g protein, 0g carbs, 5.4g fat.

Today's total: **508 kcal**.
```

---

## Example 2 — Multiple foods logged

Confirm each on its own line, then one total:
```markdown
Logged **150g of chicken breast** (meat): 248 kcal, 46.5g protein, 0g carbs, 5.4g fat.
Logged **100g of white rice** (grains): 130 kcal, 2.7g protein, 28g carbs, 0.3g fat.

Today's total: **378 kcal**.
```

---

## Example 3 — Daily totals

Tool result (`get_daily_totals_tool`):
```json
{ "success": true, "result": { "date": "2009-08-15", "calories": 508, "protein": 51.9, "carbs": 56, "fat": 6, "entries": 2 } }
```

Response:
```markdown
Today you've eaten **508 kcal** across 2 items: 51.9g protein, 56g carbs, 6g fat.
```

---

## Example 4 — Missing or zero amount (no tool called)

```markdown
How many grams of chicken did you eat?
```

---

## Example 5 — Tool failed

```markdown
Sorry, I couldn't log that food. Please try again.
```
