from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.schemas.exercise_category import ExerciseCategory
from db.schemas.exercise_entry import ExerciseEntry
from db.schemas.exercises import Exercise
from repositories.calorie_repository import find_similar
from repositories.date_ranges import iter_days


def find_exercise_category_by_name(
    db: Session, name: str
) -> Optional[ExerciseCategory]:
    """Resolve a muscle-group category by name (case-insensitive). Returns None
    for an unknown category so callers can reject it."""
    if not name:
        return None
    return (
        db.query(ExerciseCategory)
        .filter(func.lower(ExerciseCategory.name) == name.strip().lower())
        .first()
    )


def find_exercise_by_name(name: str) -> Optional[Exercise]:
    """Resolve an exercise in the shared catalog by name, tolerant of plurals
    and typos ("pushup" / "push-ups" / "push up" resolve to the same row).

    Returns the single best trigram match, or None when nothing is close
    enough. Reuses the generic `find_similar` used for food products."""
    best = find_similar(name, Exercise, limit=1, threshold=0.6)
    return best[0] if best else None


def upsert_exercise(
    db: Session,
    name: str,
    type: str,
    calories_per_rep: Optional[float] = None,
    calories_per_minute: Optional[float] = None,
    exercise_category: Optional[int] = None,
) -> Exercise:
    """Find an existing exercise by name or create it. Existing rows are
    returned unchanged (the first stored rates and category win, so known
    exercises stay stable across users)."""
    existing = find_exercise_by_name(name)
    if existing:
        return existing

    exercise = Exercise(
        name=name.strip(),
        type=type,
        calories_per_rep=calories_per_rep,
        calories_per_minute=calories_per_minute,
        exercise_category=exercise_category,
        created_at=datetime.now(),
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


def create_exercise_entry(
    db: Session,
    exercise: Exercise,
    type: str,
    created_by: int,
    reps: Optional[int] = None,
    minutes: Optional[float] = None,
) -> ExerciseEntry:
    """Log an exercise a user did, computing calories burned from the exercise's
    rate and the amount performed.

    reps-based:     calories = reps * calories_per_rep
    duration-based: calories = minutes * calories_per_minute
    """
    if type == "reps":
        calories = round((reps or 0) * (exercise.calories_per_rep or 0.0), 2)
    else:  # "duration"
        calories = round((minutes or 0) * (exercise.calories_per_minute or 0.0), 2)

    entry = ExerciseEntry(
        exercise_id=exercise.id,
        repetition=reps,
        minutes=minutes,
        calories=calories,
        exercise_category=exercise.exercise_category,
        created_at=datetime.now(),
        created_by=created_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_daily_exercise_totals(db: Session, day: date, created_by: int) -> dict:
    """Sum a user's calories burned for a single day."""
    return get_exercise_totals_in_range(db, day, day, created_by)[0]


def get_exercise_totals_in_range(
    db: Session, start: date, end: date, created_by: int
) -> list[dict]:
    """Sum a user's calories burned per day over an inclusive date range
    [start, end].

    Returns one entry per day ordered chronologically. Days with no entries are
    zero-filled so the whole range is represented."""
    day = func.date(ExerciseEntry.created_at)
    rows = (
        db.query(
            day.label("day"),
            func.coalesce(func.sum(ExerciseEntry.calories), 0.0),
            func.count(ExerciseEntry.id),
        )
        .filter(ExerciseEntry.created_by == created_by)
        .filter(ExerciseEntry.created_at >= start)
        .filter(ExerciseEntry.created_at <= end)
        .group_by(day)
        .order_by(day)
        .all()
    )

    by_day = {}
    for row in rows:
        d = row[0] if isinstance(row[0], date) else date.fromisoformat(row[0])
        by_day[d] = {
            "calories": round(row[1], 2),
            "entries": row[2],
        }

    zero = {"calories": 0.0, "entries": 0}
    return [
        {"date": d.isoformat(), **by_day.get(d, zero)}
        for d in iter_days(start, end)
    ]


def get_daily_exercises(db: Session, day: date, created_by: int) -> list[dict]:
    """List the individual exercises a user logged on a single day."""
    return get_exercises_in_range(db, day, day, created_by)


def get_exercises_in_range(
    db: Session, start: date, end: date, created_by: int
) -> list[dict]:
    """List the individual exercises a user logged over an inclusive date range
    [start, end], with the exercise name resolved from the shared catalog.

    Left-joins `exercises` so entries with a null/unknown `exercise_id` are still
    returned (name is None in that case).
    """
    rows = (
        db.query(ExerciseEntry, Exercise.name)
        .outerjoin(Exercise, ExerciseEntry.exercise_id == Exercise.id)
        .filter(ExerciseEntry.created_by == created_by)
        .filter(ExerciseEntry.created_at >= start)
        .filter(ExerciseEntry.created_at <= end)
        .order_by(ExerciseEntry.created_at, ExerciseEntry.id)
        .all()
    )

    return [
        {
            "id": entry.id,
            "name": name,
            "date": entry.created_at.isoformat(),
            "repetition": entry.repetition,
            "minutes": entry.minutes,
            "calories": round(entry.calories, 2),
        }
        for entry, name in rows
    ]
