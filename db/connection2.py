
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.db_config import DB_CONFIG

DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG.get('port', 5432)}"
    f"/{DB_CONFIG['main_database']}"
)

engine = create_engine(DATABASE_URL)

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
