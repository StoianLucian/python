from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from dotenv import load_dotenv
import os
import jwt
import bcrypt

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

def hash_password(password):
    salt = bcrypt.gensalt()
    password_bytes = password.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    
    return hashed_password
    
from typing import Union

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
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=15)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token

def verify_jwt(token: str) -> dict:
    print(JWT_SECRET, JWT_ALGORITHM)
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