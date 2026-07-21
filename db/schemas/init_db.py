from db.connection import engine
from db.schemas.Base import Base

# Import all models so they register on Base.metadata
import db.schemas  # noqa: F401

Base.metadata.create_all(bind=engine)
