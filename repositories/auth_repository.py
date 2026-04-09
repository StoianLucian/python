from fastapi import HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from db.schemas.user import User
from dto.auth.auth import LoginRequest
from services import create_jwt, verify_jwt, verify_password
from services.security import return_user_object
from sql import LOGIN_USER
import os
# load_dotenv()


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

    return {"message": "logged out"}


def get_current_user_db(user):
    if not JWT_SECRET:
        raise HTTPException(status_code=401, detail="Not authenticated")


def login_user_db(loginData: LoginRequest, response: Response, db: Session):

    user = return_user_object(loginData, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "User not found",
                "errorCode": "user_not_found"
            })

    passwordCheck = verify_password(
        loginData.password, user.password)

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
        secure=False,       # HTTPS doar în prod
        samesite="Lax",     # same-origin funcționează
        max_age=60 * 60 * 5,
        path="/"
    )
    # Remove password before returning user data to do
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
