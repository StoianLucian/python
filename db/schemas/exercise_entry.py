from datetime import datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from db.schemas.base import Base


class ExerciseEntry(Base):
    """A single logged exercise for a user on a given day.

    Calories burned are computed at log time from the exercise's rate and the
    amount performed: reps * calories_per_rep, or minutes * calories_per_minute
    (see `Exercise.type`). Scoped per user via `created_by` (injected from the
    auth cookie, never from the LLM).
    """

    __tablename__ = "exercise_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    exercise_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exercises.id"),
        nullable=True,
    )

    # The amount performed. Exactly one is set depending on the exercise type:
    # `repetition` for rep-based exercises, `minutes` for duration-based ones.
    repetition: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Calories burned for this entry, computed at log time.
    calories: Mapped[float] = mapped_column(Float, nullable=False)

    # Copied from the exercise at log time (denormalized, like the food feature).
    exercise_category: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exercise_categories.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
