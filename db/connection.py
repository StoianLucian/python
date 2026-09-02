
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schemas.base import Base

from config.db_config import resolve_db_url
from dotenv import load_dotenv

from db.schemas.food_category import seed_food_categories  # noqa: E402
from db.schemas.exercise_category import seed_exercise_categories  # noqa: E402


load_dotenv()

engine = create_engine(resolve_db_url(), pool_pre_ping=True)

import db.schemas  # noqa: F401 — register all models on Base.metadata

# Enable trigram matching before create_all so fuzzy product lookups
# (repositories.calorie_repository.find_similar_products) work on a fresh DB.
from sqlalchemy import text  # noqa: E402

with engine.begin() as _conn:
    _conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


_seed_session = SessionLocal()
try:
    seed_food_categories(_seed_session)
    seed_exercise_categories(_seed_session)
finally:
    _seed_session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
