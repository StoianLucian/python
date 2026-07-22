from fastapi import APIRouter, Depends, Query
from typing import Optional
from db.connection import get_db
from repositories.skills_repository import get_skills_db, populate_skills
from schemas import *
from sqlalchemy.orm import Session

from repositories import *

router = APIRouter(
    prefix="/skills",
    tags=["skills"],
)

@router.get("/")
def get_skills(search_term: Optional[str] = Query(None),  user=Depends(check_token), db: Session = Depends(get_db)):
    return get_skills_db(db, search_term)


