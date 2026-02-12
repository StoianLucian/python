from fastapi import APIRouter
from repositories import *
from pydantic import BaseModel
from fastapi import Response

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    account: str
    password: str

@router.post("/login")
def login_user(loginData: LoginRequest, response: Response):
    return login_user_db(loginData, response)

@router.post("/logout")
def logout_user(response: Response):
    return logout_user_db(response)
    