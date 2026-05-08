from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.connection import get_db
from errors.user import NotAuthenticatedError
from repositories import login_user_db, logout_user_db
from fastapi import Response
import logging

from repositories.auth_repository import LoginRequest, check_token
from repositories.user_repository import get_user_by_id_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login_user(loginData: LoginRequest, response: Response, db: Session = Depends(get_db)):
    logging.info(f"auth.login_user: {loginData}")
    return login_user_db(loginData, response, db)


@router.post("/logout")
def logout_user(response: Response):
    logging.info(f"auth.logout")
    return logout_user_db(response)


@router.get("/me")
def get_current_user(user=Depends(check_token), db: Session = Depends(get_db)):

    logging.info(f"auth.logout {user}")
    if not user:
        raise NotAuthenticatedError()
    user = get_user_by_id_db(user["user_id"], db)
    return user
