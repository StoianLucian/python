from datetime import datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.schemas.base import Base


class Exercise(Base):
    """A reusable, shared catalog of exercises with their calorie-burn rates.

    Burn rates are universal (a push-up burns roughly the same for everyone), so
    this table is global and NOT scoped per user. Once any user logs an exercise,
    its rates are stored here so the model never has to re-estimate them.

    `type` decides which rate is used when logging:
      - "reps"     -> calories = repetitions * calories_per_rep  (e.g. push-ups)
      - "duration" -> calories = minutes * calories_per_minute    (e.g. running)
    """

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Whether this exercise is counted by repetitions or by duration. Picks which
    # of the two rates below is authoritative for the calorie calculation.
    type: Mapped[str] = mapped_column(String, nullable=False)

    calories_per_rep: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calories_per_minute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # The muscle group (chest, back, cardio, ...). Set once when the exercise is
    # first created; the source of truth for the category.
    exercise_category: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exercise_categories.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)
