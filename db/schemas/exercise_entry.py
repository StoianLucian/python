from datetime import datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.schemas.base import Base


class ExerciseEntry(Base):
    """A single logged food item for a user on a given day.

    Totals are computed at log time from the product's per-100g macros and the
    grams eaten: total = grams / 100 * per_100g. Scoped per user via
    `created_by` (injected from the auth cookie, never from the LLM).
    """

    __tablename__ = "exercise_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    exercise_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exercises.id"),
        nullable=True,
    )

    repetition: Mapped[int] = mapped_column(Integer, nullable=False)
    # Copied from the product at log time (denormalized, like name/macros).
    exercise_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exercises.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
