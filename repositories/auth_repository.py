from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel
from services.security import create_jwt, verify_jwt, verify_password
from sql import LOGIN_USER
from context.context_manager import db_cursor
from dotenv import load_dotenv
import os

class LoginRequest(BaseModel):
    account: str
    password: str
    
TOKEN_NAME = os.getenv("TOKEN_NAME")
JWT_SECRET = os.getenv("JWT_SECRET")
    
def logout_user_db(response: Response):
    try:
        response.delete_cookie(
            key=TOKEN_NAME,
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/" 
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)   # 👈 actual error message
        )

    return {"message" : "logged out"}
    

def login_user_db(loginData: LoginRequest, response: Response):
    with db_cursor() as (_, cursor):
        cursor.execute(LOGIN_USER, (loginData.account, loginData.account))
        user = cursor.fetchone()

        if user is None:
                   raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "errorCode": "user_not_found"
                })
        
        passwordCheck = verify_password(loginData.password, user.password)

        if passwordCheck is False:
                   raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "errorCode": "user_not_found"
                })
       
        token = create_jwt(user.id)

        response.set_cookie(
            key=TOKEN_NAME,
            value=token,
            httponly=True,
            secure=True,      # HTTPS only
            samesite="Lax",   # or "Strict" / "None"
            max_age=3600
        )
        
        return user
    
def check_token(request: Request):
    token = request.cookies.get(TOKEN_NAME)
    
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Your are not authorized",
                "errorCode": "not_authorized"
            })
        
    try:
        payload = verify_jwt(token)
        return payload
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Your are not authorized",
                "errorCode": "not_authorized"
            }
        )
