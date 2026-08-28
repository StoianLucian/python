# Skill: Calorie & Macro Tracking

## Purpose



## Workflow — logging food

For **each** food the user mentions:



## Workflow — daily totals

If the user asks what they have eaten, how many calories they have had, or for a
day's totals, call `get_daily_totals_tool`
## Food categories

When calling `add_food_entry`, classify the food into exactly ONE `category`
from this fixed list (use the exact spelling):

`vegetable`, `fruit`, `meat`, `seafood`, `dairy`, `grains`, `legumes`,
`sweets`, `beverages`, `snacks`, `fats_oils`, `other`

Pick the best fit (e.g. chicken → `meat`, banana → `fruit`, chocolate →
`sweets`, olive oil → `fats_oils`). Use `other` only when nothing fits. Never
invent a category outside this list — the tool rejects unknown values.

## Rules

- Always pass macros PER 100g to `add_food_entry` — never the total for the
  eaten amount. The tool computes the totals itself.
- Always pass a `category` from the fixed list above when logging a food.
- Do NOT provide a `created_by` value; user identity is attached automatically.
- If the user names a food but gives no amount in grams, or gives `0` grams, do
  NOT guess and do NOT call any tool — ask them for the quantity in grams first.
- Handle multiple foods in a single message by looping the workflow per food.
- Never invent the results of a tool call.
