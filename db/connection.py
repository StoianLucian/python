
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schemas.base import Base

from config.db_config import DB_CONFIG
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG.get('port', 5432)}"
    f"/{DB_CONFIG['main_database']}"
)

DB_URL = os.getenv("DB_URL")

engine = create_engine(DB_URL or DATABASE_URL, pool_pre_ping=True)

import db.schemas  # noqa: F401 — register all models on Base.metadata

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
