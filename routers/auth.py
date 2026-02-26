from fastapi import APIRouter, Depends
from errors.user import NotAuthenticatedError
from repositories import login_user_db, logout_user_db
from pydantic import BaseModel
from fastapi import Response

from repositories.auth_repository import check_token, get_current_user_db
from repositories.user_repository import get_user_by_id_db

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    account: str
    password: str

@router.post("/login")
def login_user(loginData: LoginRequest, response: Response):
    login_dict = loginData.model_dump()
    return login_user_db(login_dict, response)


@router.post("/logout")
def logout_user(response: Response):
    return logout_user_db(response)


@router.get("/me")
def get_current_user(user=Depends(check_token)):
    if not user:
        raise NotAuthenticatedError()
    user = get_user_by_id_db(user["user_id"])
    return user
