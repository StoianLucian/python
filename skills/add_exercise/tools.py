import json
import re
import statistics
from datetime import date, datetime
from typing import Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from db.connection import SessionLocal
from db.schemas.exercise_category import DEFAULT_EXERCISE_CATEGORIES, ExerciseCategory
from import_folder.response import ToolResponse
from lmm.factory import get_lmm_provider
from repositories.exercise_repository import (
    create_exercise_entry,
    find_exercise_by_name,
    find_exercise_category_by_name,
    get_daily_exercise_totals,
    upsert_exercise,
)
from services.search import search_web
from tools.helpers import get_category_name


class ExerciseLookup(BaseModel):
    found: bool
    name: str
    source: Optional[str] = None  # "catalog" or "web" when found
    # set when a catalog exercise is categorized
    category: Optional[str] = None
    type: Optional[str] = None  # "reps" or "duration"
    calories_per_rep: Optional[float] = None
    calories_per_minute: Optional[float] = None


class _ExerciseExtraction(BaseModel):
    """Schema the extraction model is forced to emit (via Ollama's `format`).
    Constrains decoding to the burn rates and the type, so the reply is always
    valid JSON in this shape — no prose, fences, or reasoning to scrape."""

    type: Optional[str] = None
    calories_per_rep: Optional[float] = None
    calories_per_minute: Optional[float] = None


# JSON Schema passed as Ollama's `format=` to enforce structured output.
_EXERCISE_FORMAT = _ExerciseExtraction.model_json_schema()

_EXTRACTION_SYSTEM_PROMPT = (
    "You estimate how many calories an exercise burns for an average 70 kg "
    "adult, using web search snippets as a guide.\n\n"
    "OUTPUT FORMAT — follow exactly:\n"
    "- Respond with a SINGLE raw JSON object and NOTHING else, starting with "
    "'{' and ending with '}'.\n"
    "- Do NOT include markdown, code fences (```), explanations, or any "
    "reasoning/thinking text. /no_think\n"
    "- Use exactly these keys with plain JSON numbers (no units, no quotes) or "
    "null:\n"
    '{"type": "reps"|"duration", "calories_per_rep": <kcal>, '
    '"calories_per_minute": <kcal>}\n\n'
    "RULES:\n"
    "- `type` is \"reps\" for exercises counted in repetitions (push-ups, "
    "squats, sit-ups, pull-ups, lunges) and \"duration\" for time-based "
    "exercises (running, cycling, swimming, walking, planks, jumping jacks).\n"
    "- For a \"reps\" exercise you MUST give a POSITIVE calories_per_rep and set "
    "calories_per_minute to null. Per-rep is a small DECIMAL — never 0 and never "
    "a whole number like 5. Typical anchors: push-up ~0.3, sit-up ~0.15, squat "
    "~0.32, pull-up ~1.0, burpee ~0.5, lunge ~0.35. If the snippets only give "
    "per-minute, ESTIMATE per-rep from these anchors.\n"
    "- For a \"duration\" exercise give calories_per_minute and set "
    "calories_per_rep to null.\n"
    "- Never output 0. If truly unknown, use your best positive estimate."
)


def _parse_exercise(text: str) -> Optional[dict]:
    """Pull the first JSON object out of the model's reply and keep the type and
    the burn rate that matches it. Returns None on an unusable extraction."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (ValueError, TypeError):
        return None

    ex_type = data.get("type")
    if ex_type not in ("reps", "duration"):
        return None

    per_rep = data.get("calories_per_rep")
    per_minute = data.get("calories_per_minute")

    # The rate that matches the type must be a usable positive number.
    rate = per_rep if ex_type == "reps" else per_minute
    if not isinstance(rate, (int, float)) or rate <= 0:
        return None

    return {
        "type": ex_type,
        "calories_per_rep": float(per_rep) if isinstance(per_rep, (int, float)) else None,
        "calories_per_minute": float(per_minute) if isinstance(per_minute, (int, float)) else None,
    }


def _aggregate_exercise(candidates: list[dict]) -> Optional[dict]:
    """Verification step: reduce several per-source extractions to one result.
    The `type` is a majority vote; the matching burn rate is the MEDIAN across
    the sources that agreed on that type, so one outlier can't skew it. None if
    no candidates."""
    if not candidates:
        return None

    types = [c["type"] for c in candidates]
    ex_type = max(set(types), key=types.count)
    matching = [c for c in candidates if c["type"] == ex_type]

    rate_key = "calories_per_rep" if ex_type == "reps" else "calories_per_minute"
    values = [c[rate_key] for c in matching if isinstance(c.get(rate_key), (int, float))]
    if not values:
        return None

    median = round(statistics.median(values), 3)
    return {
        "type": ex_type,
        "calories_per_rep": median if ex_type == "reps" else None,
        "calories_per_minute": median if ex_type == "duration" else None,
    }


def _search_exercise_calories(name: str) -> Optional[dict]:
    """Search the web and extract the type + burn rate from up to THREE
    independent sources, then verify: majority-vote the type and take the median
    rate across the agreeing sources. Returns None if nothing usable."""
    query = f"{name} calories burned per rep and per minute average adult"
    response = search_web(query)
    if not response:
        return None

    # Up to three distinct sources: Tavily's answer summary (when present) plus
    # the highest-scored result snippets.
    sources = []
    if response.get("answer"):
        sources.append(response["answer"])
    sources.extend(
        r["content"] for r in response.get("results", []) if r.get("content"))
    sources = sources[:3]

    candidates = []
    for i, source in enumerate(sources, 1):
        reply = get_lmm_provider().chat(
            "granite4.1:3b",
            [
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Exercise: {name}\n\nSource:\n{source}"},
            ],
            format=_EXERCISE_FORMAT,
        )
        parsed = _parse_exercise(reply.message.content)
        print(f"[verify][exercise] {name} source {i}/{len(sources)} -> {parsed}")
        if parsed:
            candidates.append(parsed)

    verified = _aggregate_exercise(candidates)
    print(f"[verify][exercise] {name} verified from {len(candidates)} source(s) -> {verified}")
    return verified


class LoggedExercise(BaseModel):
    name: str
    type: str
    reps: Optional[int] = None
    minutes: Optional[float] = None
    category: Optional[str] = None
    calories_burned: float
    # user's total kcal burned today after this entry
    today_total_calories_burned: float = 0.0


def register_exercises_tools(mcp: FastMCP):

    @mcp.tool
    async def lookup_exercise(name: str) -> ToolResponse:
        """
        STEP 1 of logging an exercise. Resolve an exercise's calorie-burn rate:
        checks the shared catalog first and, on a miss, searches the web for the
        burn rate automatically.

        You MUST call this FIRST for each exercise the user mentions, BEFORE
        `add_exercise_entry` — that tool needs the `type` and rate this returns,
        and you must never invent them. If `found` is true, pass the returned
        `type` and rate straight to `add_exercise_entry` (STEP 2). If `found` is
        false, the rate could not be determined; tell the user you couldn't find
        data for that exercise and do NOT call `add_exercise_entry` for it.

        Args:
            name: The exercise name, e.g. "push-ups", "running".
        """
        db = SessionLocal()
        try:
            exercise = find_exercise_by_name(name)
            print(exercise, "catalog hit=====" if exercise else "catalog miss=====")
            if exercise:
                return ToolResponse(
                    success=True,
                    result=ExerciseLookup(
                        found=True,
                        name=exercise.name,
                        source="catalog",
                        category=get_category_name(
                            db, exercise.exercise_category, ExerciseCategory),
                        type=exercise.type,
                        calories_per_rep=exercise.calories_per_rep,
                        calories_per_minute=exercise.calories_per_minute,
                    ),
                )

            # Not in the catalog — fall back to a web search + extraction so the
            # model gets a usable rate without having to chain another tool.
            data = _search_exercise_calories(name)
            if data:
                return ToolResponse(
                    success=True,
                    result=ExerciseLookup(
                        found=True,
                        name=name,
                        source="web",
                        **data,
                    ),
                )

            return ToolResponse(
                success=True,
                result=ExerciseLookup(found=False, name=name),
            )
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()

    @mcp.tool
    async def add_exercise_entry(
        name: str,
        type: str,
        category: str,
        reps: Optional[int] = None,
        minutes: Optional[float] = None,
        calories_per_rep: Optional[float] = None,
        calories_per_minute: Optional[float] = None,
        created_by: Optional[int] = None,
    ) -> ToolResponse:
        """
        STEP 2 of logging an exercise — this is the tool that ACTUALLY logs it.
        Logging is not complete until this has run successfully.

        Do NOT call this until `lookup_exercise` has returned `found: true` for
        this exercise; pass the EXACT `type`, `calories_per_rep`/
        `calories_per_minute` from that result — never invent or guess them. If
        you don't have a `lookup_exercise` result for this exercise yet, call
        `lookup_exercise` first.

        Pass the `type` and rate returned by `lookup_exercise`. Calories burned
        are computed and returned:
          - type "reps":     calories = reps * calories_per_rep
          - type "duration": calories = minutes * calories_per_minute

        Only call this once you have the amount the type needs. For a "reps"
        exercise you MUST have a positive `reps`; for a "duration" exercise you
        MUST have positive `minutes`. If the needed amount is missing or 0, do
        NOT call this tool — ask the user for it instead.

        Classify the exercise into exactly ONE of these muscle-group categories
        and pass it as `category`: chest, back, shoulders, biceps, triceps,
        forearms, core, glutes, quadriceps, hamstrings, calves, hips, full_body,
        cardio, other. Use "other" if none fit.

        Args:
            name: The exercise name.
            type: "reps" or "duration".
            category: One of the allowed muscle-group categories listed above.
            reps: Repetitions performed (for a "reps" exercise).
            minutes: Minutes performed (for a "duration" exercise).
            calories_per_rep: Calories (kcal) burned per repetition.
            calories_per_minute: Calories (kcal) burned per minute.
        """
        print("========= exercise entry", name, type, reps, minutes, category)
        db = SessionLocal()
        try:
            if type not in ("reps", "duration"):
                return ToolResponse(
                    success=False,
                    result="type must be 'reps' or 'duration'.",
                )

            if type == "reps" and not reps:
                return ToolResponse(
                    success=False,
                    result="A 'reps' exercise needs a positive `reps` amount.",
                )
            if type == "duration" and not minutes:
                return ToolResponse(
                    success=False,
                    result="A 'duration' exercise needs a positive `minutes` amount.",
                )

            resolved_category = find_exercise_category_by_name(db, category)
            if resolved_category is None:
                return ToolResponse(
                    success=False,
                    result=(
                        f"Unknown category '{category}'. Choose one of: "
                        f"{', '.join(DEFAULT_EXERCISE_CATEGORIES)}."
                    ),
                )

            exercise = upsert_exercise(
                db,
                name=name,
                type=type,
                calories_per_rep=calories_per_rep,
                calories_per_minute=calories_per_minute,
                exercise_category=resolved_category.id,
            )
            entry = create_exercise_entry(
                db,
                exercise=exercise,
                type=type,
                reps=reps,
                minutes=minutes,
                created_by=created_by,
            )
            # Running total for today, so the reply can show it alongside the
            # logged exercise without relying on a separate tool call.
            today_totals = get_daily_exercise_totals(
                db, date.today(), created_by)
            return ToolResponse(
                success=True,
                result=LoggedExercise(
                    name=exercise.name,
                    type=type,
                    reps=entry.repetition,
                    minutes=entry.minutes,
                    category=get_category_name(
                        db, entry.exercise_category, ExerciseCategory),
                    calories_burned=entry.calories,
                    today_total_calories_burned=today_totals["calories"],
                ),
            )
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()

    @mcp.tool
    async def get_exercise_daily_totals(
        created_by: Optional[int] = None,
    ) -> ToolResponse:
        """
        Return the user's total calories burned for TODAY. Use this when the user
        asks how much they've exercised or how many calories they've burned.

        Takes no arguments — it always reports today's totals for the current
        user. Do NOT pass a date.
        """
        db = SessionLocal()
        try:
            totals = get_daily_exercise_totals(
                db, datetime.now().date(), created_by=created_by)
            return ToolResponse(success=True, result=totals)
        except Exception as e:
            return ToolResponse(success=False, result=f"Error: {e}")
        finally:
            db.close()
