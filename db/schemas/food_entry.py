from datetime import datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.schemas.base import Base


class FoodEntry(Base):
    """A single logged food item for a user on a given day.

    Totals are computed at log time from the product's per-100g macros and the
    grams eaten: total = grams / 100 * per_100g. Scoped per user via
    `created_by` (injected from the auth cookie, never from the LLM).
    """

    __tablename__ = "food_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("food_products.id"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)

    grams: Mapped[float] = mapped_column(Float, nullable=False)

    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)

    # Copied from the product at log time (denormalized, like name/macros).
    food_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("food_categories.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(Date, nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
