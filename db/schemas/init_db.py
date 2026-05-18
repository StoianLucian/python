from db.database import engine
from db.schemas.Base import Base

# IMPORT ALL MODELS
import db.schemas.ChatSession
import db.schemas.ChatMessage

Base.metadata.create_all(bind=engine)