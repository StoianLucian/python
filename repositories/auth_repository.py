from fastapi import HTTPException, Response
from pydantic import BaseModel
from services.security import create_jwt, verify_password
from sql import LOGIN_USER
from context.context_manager import db_cursor
from datetime import datetime, timedelta, timezone

class LoginRequest(BaseModel):
    account: str
    password: str

def login_user_db(loginData: LoginRequest, response: Response):
    with db_cursor() as (_, cursor):
        cursor.execute(LOGIN_USER, (loginData.account, loginData.account))
        user = cursor.fetchone()

        if user is None:
                   raise HTTPException(
                status_code=404,
                detail={
                    "message": "User not found",
                    "errorCode": "user_not_found"
                })

        
        passwordCheck = verify_password(loginData.password, user.password)

        if passwordCheck is False:
                   raise HTTPException(
                status_code=404,
                detail={
                    "message": "User not found",
                    "errorCode": "user_not_found"
                })
       
        token = create_jwt(user.id)

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,      # HTTPS only
            samesite="Lax",   # or "Strict" / "None"
            max_age=3600
        )
        
        return user