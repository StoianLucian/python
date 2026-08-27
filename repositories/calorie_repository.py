from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.connection import SessionLocal
from db.schemas.food_category import FoodCategory
from db.schemas.food_entry import FoodEntry
from db.schemas.food_product import FoodProduct


def find_category_by_name(db: Session, name: str) -> Optional[FoodCategory]:
    """Resolve a category by name (case-insensitive). Returns None for an
    unknown category so callers can reject it."""
    if not name:
        return None
    return (
        db.query(FoodCategory)
        .filter(func.lower(FoodCategory.name) == name.strip().lower())
        .first()
    )


def get_category_name(db: Session, category_id: Optional[int]) -> Optional[str]:
    """Return the category name for an id, or None."""
    if category_id is None:
        return None
    category = db.get(FoodCategory, category_id)
    return category.name if category else None


def find_product_by_name(name: str) -> Optional[FoodProduct]:
    """Resolve a product in the shared catalog by name, tolerant of plurals and
    typos ("potato" / "potatoes" / "potatoe" all resolve to the same row).

    Returns the single best trigram match, or None when nothing is close
    enough. Used on the identity/dedup path (lookup + upsert), so the threshold
    is stricter than `find_similar_products` to avoid merging distinct foods
    (e.g. "chicken" vs "chicken breast")."""
    best = find_similar_products(name, limit=1, threshold=0.6)
    return best[0] if best else None


def find_similar_products(
    name: str,
    limit: int = 5,
    threshold: float = 0.3,
) -> List[FoodProduct]:
    db = SessionLocal()
    normalized = name.strip().lower()
    if not normalized:
        return []

    score = func.similarity(func.lower(FoodProduct.name), normalized)
    return (
        db.query(FoodProduct)
        .filter(score >= threshold)
        .order_by(score.desc())
        .limit(limit)
        .all()
    )


def upsert_product(
    db: Session,
    name: str,
    calories_per_100g: float,
    protein_per_100g: float,
    carbs_per_100g: float,
    fat_per_100g: float,
    food_category_id: Optional[int] = None,
) -> FoodProduct:
    """Find an existing product by name or create it. Existing rows are
    returned unchanged (the first stored macros and category win, so known
    foods stay stable across users)."""
    existing = find_product_by_name(name)
    if existing:
        return existing

    product = FoodProduct(
        name=name.strip(),
        calories_per_100g=calories_per_100g,
        protein_per_100g=protein_per_100g,
        carbs_per_100g=carbs_per_100g,
        fat_per_100g=fat_per_100g,
        food_category_id=food_category_id,
        created_at=datetime.now(),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def create_food_entry(
    db: Session,
    product: FoodProduct,
    grams: float,
    created_by: int,
) -> FoodEntry:
    """Log `grams` of `product` for a user, computing totals from the
    product's per-100g macros."""
    factor = grams / 100.0

    entry = FoodEntry(
        product_id=product.id,
        name=product.name,
        grams=grams,
        calories=round(product.calories_per_100g * factor, 2),
        protein=round(product.protein_per_100g * factor, 2),
        carbs=round(product.carbs_per_100g * factor, 2),
        fat=round(product.fat_per_100g * factor, 2),
        food_category_id=product.food_category_id,
        created_at=datetime.now(),
        created_by=created_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_daily_totals(db: Session, day: date, created_by: int) -> dict:
    """Sum a user's macros for a single day."""
    row = (
        db.query(
            func.coalesce(func.sum(FoodEntry.calories), 0.0),
            func.coalesce(func.sum(FoodEntry.protein), 0.0),
            func.coalesce(func.sum(FoodEntry.carbs), 0.0),
            func.coalesce(func.sum(FoodEntry.fat), 0.0),
            func.count(FoodEntry.id),
        )
        .filter(FoodEntry.created_by == created_by)
        .filter(FoodEntry.created_at == day)
        .one()
    )

    return {
        "date": day.isoformat(),
        "calories": round(row[0], 2),
        "protein": round(row[1], 2),
        "carbs": round(row[2], 2),
        "fat": round(row[3], 2),
        "entries": row[4],
    }
