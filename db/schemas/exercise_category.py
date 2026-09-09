from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from db.schemas.base import Base


class ExerciseCategory(Base):
    """A fixed catalog of exercise categories (muscle groups: chest, back,
    cardio, ...).

    Referenced by `exercises.exercise_category` (the source of truth for an
    exercise's category) and denormalized onto `exercise_entry.exercise_category`
    at log time.
    """

    __tablename__ = "exercise_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )


DEFAULT_EXERCISE_CATEGORIES = [
    "chest",
    "back",
    "shoulders",
    "biceps",
    "triceps",
    "forearms",
    "core",
    "glutes",
    "quadriceps",
    "hamstrings",
    "calves",
    "hips",
    "full_body",
    "cardio",
    "other",
]


def seed_exercise_categories(db: Session) -> None:
    """Insert any missing default categories. Idempotent — safe to call on
    every startup."""
    existing = {
        name.lower()
        for (name,) in db.query(ExerciseCategory.name).all()
    }
    added = False
    for name in DEFAULT_EXERCISE_CATEGORIES:
        if name.lower() not in existing:
            db.add(ExerciseCategory(name=name))
            added = True
    if added:
        db.commit()
