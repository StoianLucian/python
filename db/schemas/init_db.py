from db.database import engine
from db.schemas.Base import Base

# IMPORT ALL MODELS
import db.schemas

Base.metadata.create_all(bind=engine)