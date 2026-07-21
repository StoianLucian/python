from typing import Union
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import or_
from sqlalchemy.orm import Session
from db.schemas.user import User
from errors.user import AccountAlreadyExistsError, UserNotFoundError
from repositories.auth_repository import LoginRequest
from schemas.user_schemas import UserCreate
import os
import jwt
import bcrypt

load_dotenv()

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")  # default to HS256

TOKEN_NAME = os.getenv("TOKEN_NAME")
JWT_SECRET = os.getenv("JWT_SECRET")


def hash_password(password):
    salt = bcrypt.gensalt()
    password_bytes = password.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, salt)

    return hashed_password


def check_existing_user(user: UserCreate, db: Session):
    existing = db.query(User).filter(
        or_(
            User.email == user.email,
            User.username == user.username
        )).first()

    if existing:
        raise AccountAlreadyExistsError()


def check_match_password(password: str, confirmPassword: str):
    if password != confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Passwords do not match",
                "errorCode": "password_mismatch"
            })


def verify_password(password: str, hashed_password: Union[str, bytes]) -> bool:
    """
    Verifică parola.
    """
    # Dacă e string PostgreSQL BYTEA, convertim la bytes
    if isinstance(hashed_password, str):
        hex_str = hashed_password
        if hex_str.startswith("\\x"):
            hex_str = hex_str[2:]
        hashed_password_bytes = bytes.fromhex(hex_str)
    else:
        hashed_password_bytes = hashed_password

    # verificare cu bcrypt
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password_bytes)


def create_jwt(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=5)  # align with auth cookie max_age
    }

    if not JWT_ALGORITHM or not JWT_SECRET:
        raise RuntimeError("env not loaded")

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def verify_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Token expired",
                "errorCode": "token_expired"
            }
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Invalid token",
                "errorCode": "invalid_token"
            }
        )


def return_user_object(loginData: LoginRequest, db: Session):
    
    account = loginData.account
    
    user = db.query(User).filter(
        or_(
            User.email == account,
            User.username == account
        )).first()

    if not user:
        raise UserNotFoundError()

    return user
