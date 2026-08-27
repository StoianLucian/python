from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from db.schemas.base import Base


class FoodCategory(Base):
    """A fixed catalog of food categories (vegetable, meat, sweets, ...).

    Referenced by `food_products.food_category_id` (the source of truth for a
    food's category) and denormalized onto `food_entries.food_category_id` at
    log time.
    """

    __tablename__ = "food_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )


# The canonical set the LLM classifies foods into. "other" is the safe fallback
# so classification always resolves to a valid category.
DEFAULT_FOOD_CATEGORIES = [
    "vegetable",
    "fruit",
    "meat",
    "seafood",
    "dairy",
    "grains",
    "legumes",
    "sweets",
    "beverages",
    "snacks",
    "fats_oils",
    "other",
]


def seed_food_categories(db: Session) -> None:
    """Insert any missing default categories. Idempotent — safe to call on
    every startup."""
    existing = {
        name.lower()
        for (name,) in db.query(FoodCategory.name).all()
    }
    added = False
    for name in DEFAULT_FOOD_CATEGORIES:
        if name.lower() not in existing:
            db.add(FoodCategory(name=name))
            added = True
    if added:
        db.commit()
