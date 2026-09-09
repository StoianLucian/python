from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.schemas.exercise_category import ExerciseCategory
from db.schemas.exercise_entry import ExerciseEntry
from db.schemas.exercises import Exercise
from repositories.calorie_repository import find_similar


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
    row = (
        db.query(
            func.coalesce(func.sum(ExerciseEntry.calories), 0.0),
            func.count(ExerciseEntry.id),
        )
        .filter(ExerciseEntry.created_by == created_by)
        .filter(ExerciseEntry.created_at == day)
        .one()
    )

    return {
        "date": day.isoformat(),
        "calories": round(row[0], 2),
        "entries": row[1],
    }
