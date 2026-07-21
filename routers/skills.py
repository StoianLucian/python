from fastapi import APIRouter, Depends
from db.connection import get_db
from repositories.skills_repository import populate_skills
from schemas import *
from sqlalchemy.orm import Session

from repositories import *

router = APIRouter(
    prefix="/skills",
    tags=["skills"],
)

@router.get("/")
def get_all_users(user=Depends(check_token), db: Session = Depends(get_db)):
    try:
        users = populate_skills(db)
        return users
    except Exception as e:
        raise e


