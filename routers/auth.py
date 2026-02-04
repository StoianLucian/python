from fastapi import APIRouter
from repositories import *
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    account: str
    password: str

@router.post("/login")
def login_user(loginData: LoginRequest):
    return login_user_db(loginData)
    