from fastapi import APIRouter
from repositories import *
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class UserData(BaseModel):
    username: str
    password: str

@router.post("/login")
def login_user(userData: UserData):
    return login_user_db(userData)
    