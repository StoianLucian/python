from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi import HTTPException

from db.connection import get_db
from repositories import *
from repositories.calorie_repository import (
    find_product_by_name,
    get_foods_in_range,
    get_totals_in_range,
)
from repositories.exercise_repository import (
    get_exercise_totals_in_range,
    get_exercises_in_range,
)
from skills.add_calories.tools import ProductLookup, _search_food_macros

router = APIRouter(
    prefix="/calories",
    tags=["calories"],
)


@router.get("/lookup")
def lookup_food_macros(
    name: str = Query(..., min_length=1, description="Food name, e.g. 'chicken breast'"),
    user=Depends(check_token),
):
    """Look up a food's per-100g macros via web search + extraction.

    Wraps `_search_food_macros`: searches the web for the food and returns the
    first source whose extracted macros pass the plausibility check. Returns
    `found: false` when no source yields usable macros.

    This is a plain (non-async) handler on purpose — `_search_food_macros` does
    blocking network + model calls, so FastAPI runs it in a threadpool and the
    event loop is not blocked.
    """
    # product = find_product_by_name(name)
    # print(product, "-===========")
    macros = _search_food_macros(name)
    if macros is None:
        return ProductLookup(found=False, name=name)
    return macros


@router.get("/daily")
def daily_summary(
    day: date | None = Query(
        default=None,
        description="Single day to summarize (YYYY-MM-DD). Ignored when "
        "start/end are given; defaults to today when nothing is provided.",
    ),
    start: date | None = Query(
        default=None,
        description="Start of an inclusive date range (YYYY-MM-DD).",
    ),
    end: date | None = Query(
        default=None,
        description="End of an inclusive date range (YYYY-MM-DD).",
    ),
    user=Depends(check_token),
    db: Session = Depends(get_db),
):
    """Table summary for the currently logged-in user: one row per day with the
    calories consumed (food) and calories burned (exercise) totals.

    This returns only what the table needs. To get the individual foods and
    exercises for a given day, call `GET /calories/daily/{day}`.

    Filtering (all inclusive):
      - no params        -> today
      - ?day=YYYY-MM-DD  -> that single day
      - ?start=&end=     -> the [start, end] range (either bound may be omitted
                            to leave that side open, but at least one is required)

    The user is taken from the auth cookie (`check_token`); all queries are
    scoped to `created_by == user["user_id"]`.
    """
    if start is not None or end is not None:
        range_start = start or end
        range_end = end or start
        if range_start > range_end:
            raise HTTPException(
                status_code=422,
                detail="`start` must not be after `end`.",
            )
        if (range_end - range_start).days > 366:
            raise HTTPException(
                status_code=422,
                detail="Date range too large (max 366 days).",
            )
    else:
        single = day or date.today()
        range_start = range_end = single

    uid = user["user_id"]

    daily_totals = get_totals_in_range(db, range_start, range_end, uid)
    exercise_daily_totals = get_exercise_totals_in_range(db, range_start, range_end, uid)

    # Both lists are zero-filled over the same range, so they align by date.
    burned_by_day = {row["date"]: row for row in exercise_daily_totals}
    rows = [
        {
            # Rows are per-day aggregates keyed by the day, so `date` is the row
            # identifier. Pass it to `GET /calories/daily/{date}` to fetch that
            # day's entries and full macro/exercise breakdown.
            "date": row["date"],
            "calories_consumed": row["calories"],
            "calories_burned": burned_by_day.get(row["date"], {}).get("calories", 0.0),
        }
        for row in daily_totals
    ]

    return {
        "start": range_start.isoformat(),
        "end": range_end.isoformat(),
        "rows": rows,
    }


@router.get("/daily/{day}")
def daily_detail(
    day: date,
    user=Depends(check_token),
    db: Session = Depends(get_db),
):
    """Detail for a single day: the day's macro/exercise totals plus the
    individual food and exercise entries the logged-in user logged on `day`.

    Called when a row is clicked in the table produced by `GET /calories/daily`
    (which returns only id/date/calories per row). All queries are scoped to the
    authenticated user.
    """
    uid = user["user_id"]

    food_totals = get_totals_in_range(db, day, day, uid)[0]
    exercise_totals = get_exercise_totals_in_range(db, day, day, uid)[0]
    foods = get_foods_in_range(db, day, day, uid)
    exercises = get_exercises_in_range(db, day, day, uid)

    return {
        "date": day.isoformat(),
        "totals": {
            "calories_consumed": food_totals["calories"],
            "protein": food_totals["protein"],
            "carbs": food_totals["carbs"],
            "fat": food_totals["fat"],
            "food_entries": food_totals["entries"],
            "calories_burned": exercise_totals["calories"],
            "exercise_entries": exercise_totals["entries"],
        },
        "foods": foods,
        "exercises": exercises,
    }
