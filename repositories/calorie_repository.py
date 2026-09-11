from datetime import date, datetime
from typing import List, Optional, Type

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.connection import SessionLocal
from repositories.date_ranges import iter_days
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

def find_product_by_name(name: str) -> Optional[FoodProduct]:
    """Resolve a product in the shared catalog by name, tolerant of plurals and
    typos ("potato" / "potatoes" / "potatoe" all resolve to the same row).

    Returns the single best trigram match, or None when nothing is close
    enough. Used on the identity/dedup path (lookup + upsert), so the threshold
    is stricter than `find_similar_products` to avoid merging distinct foods
    (e.g. "chicken" vs "chicken breast")."""
    best = find_similar(name, FoodProduct, limit=1, threshold=0.6,)
    return best[0] if best else None


def find_similar(
    name: str,
    entity_type: Type,
    limit: int = 5,
    threshold: float = 0.3,
) -> List[Type]:
    db = SessionLocal()
    normalized = name.strip().lower()
    if not normalized:
        return []

    score = func.similarity(func.lower(entity_type.name), normalized)
    return (
        db.query(entity_type)
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
    return get_totals_in_range(db, day, day, created_by)[0]


def get_totals_in_range(
    db: Session, start: date, end: date, created_by: int
) -> List[dict]:
    """Sum a user's macros per day over an inclusive date range [start, end].

    Returns one entry per day ordered chronologically. Days with no entries are
    zero-filled so the whole range is represented."""
    day = func.date(FoodEntry.created_at)
    rows = (
        db.query(
            day.label("day"),
            func.coalesce(func.sum(FoodEntry.calories), 0.0),
            func.coalesce(func.sum(FoodEntry.protein), 0.0),
            func.coalesce(func.sum(FoodEntry.carbs), 0.0),
            func.coalesce(func.sum(FoodEntry.fat), 0.0),
            func.count(FoodEntry.id),
        )
        .filter(FoodEntry.created_by == created_by)
        .filter(FoodEntry.created_at >= start)
        .filter(FoodEntry.created_at <= end)
        .group_by(day)
        .order_by(day)
        .all()
    )

    by_day = {}
    for row in rows:
        d = row[0] if isinstance(row[0], date) else date.fromisoformat(row[0])
        by_day[d] = {
            "calories": round(row[1], 2),
            "protein": round(row[2], 2),
            "carbs": round(row[3], 2),
            "fat": round(row[4], 2),
            "entries": row[5],
        }

    zero = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "entries": 0}
    return [
        {"date": d.isoformat(), **by_day.get(d, zero)}
        for d in iter_days(start, end)
    ]


def get_foods_in_range(
    db: Session, start: date, end: date, created_by: int
) -> list[dict]:
    """List the individual food entries a user logged over an inclusive date
    range [start, end], with the product name resolved from the shared catalog.

    Intended for charting, so each entry carries its own macros and date.
    Left-joins `food_products` so entries with a null/unknown `product_id` are
    still returned (name is None in that case).
    """
    rows = (
        db.query(FoodEntry, FoodProduct.name)
        .outerjoin(FoodProduct, FoodEntry.product_id == FoodProduct.id)
        .filter(FoodEntry.created_by == created_by)
        .filter(FoodEntry.created_at >= start)
        .filter(FoodEntry.created_at <= end)
        .order_by(FoodEntry.created_at, FoodEntry.id)
        .all()
    )

    return [
        {
            "id": entry.id,
            "name": name,
            "date": entry.created_at.isoformat(),
            "grams": entry.grams,
            "calories": round(entry.calories, 2),
            "protein": round(entry.protein, 2),
            "carbs": round(entry.carbs, 2),
            "fat": round(entry.fat, 2),
        }
        for entry, name in rows
    ]
