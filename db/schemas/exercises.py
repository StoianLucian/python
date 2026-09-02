from datetime import datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.schemas.base import Base


class Exercise(Base):
    """A reusable, shared catalog of foods with their macros per 100g.

    Macros are universal (100g of chicken is the same for everyone), so this
    table is global and NOT scoped per user. Once any user logs a food, its
    per-100g values are stored here so the model never has to re-estimate it.
    """

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    calories_per_rep: Mapped[float] = mapped_column(Float, nullable=True)
    calories_per_minute: Mapped[float] = mapped_column(Float, nullable=True)

    # The food's category (vegetable, meat, sweets, ...). Set once when the
    # product is first created; the source of truth for the category.
    exercise_category: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exercise_categories.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)
