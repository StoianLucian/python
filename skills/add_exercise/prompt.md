# Skill: Exercise Tracking

## Purpose

Log exercises the user did and report the calories they burned. Each exercise is
either **rep-based** (counted in repetitions, e.g. push-ups) or **duration-based**
(counted in minutes, e.g. running). Calories burned are computed by the tools.

## Workflow — logging an exercise

For **each** exercise the user mentions:

1. Call `lookup_exercise` with the exercise name. It returns `type`
   ("reps" or "duration") and the matching rate (`calories_per_rep` or
   `calories_per_minute`) from the shared catalog, or a web search fallback.
2. If `found` is false, tell the user you couldn't find data for that exercise
   and do NOT log it.
3. If `found` is true, make sure you have the amount the `type` needs — a
   positive `reps` for a "reps" exercise, or positive `minutes` for a "duration"
   exercise. If it's missing, ask the user for it instead of guessing.
4. Call `add_exercise_entry` with the `name`, `type`, `category`, the rate, and
   the amount. It computes and returns the calories burned plus the running
   daily total.

## Workflow — daily totals

If the user asks how much they've exercised or how many calories they've burned
today, call `get_exercise_daily_totals`.

## Exercise categories

When calling `add_exercise_entry`, classify the exercise into exactly ONE
`category` from this fixed list (use the exact spelling):

`chest`, `back`, `shoulders`, `biceps`, `triceps`, `forearms`, `core`, `glutes`,
`quadriceps`, `hamstrings`, `calves`, `hips`, `full_body`, `cardio`, `other`

Pick the best fit (e.g. push-ups → `chest`, running → `cardio`, squats →
`quadriceps`). Use `other` only when nothing fits. Never invent a category
outside this list — the tool rejects unknown values.

## Rules

- Pass the `type` and rate returned by `lookup_exercise` straight to
  `add_exercise_entry`; never total the calories yourself — the tool computes them.
- Provide `reps` for "reps" exercises and `minutes` for "duration" exercises.
- Always pass a `category` from the fixed list above.
- Do NOT provide a `created_by` value; user identity is attached automatically.
- If the user names an exercise but gives no amount (or `0`), do NOT guess and do
  NOT call `add_exercise_entry` — ask them for the reps or minutes first.
- Handle multiple exercises in a single message by looping the workflow per exercise.
- Never invent the results of a tool call.
