from datetime import datetime, timedelta, timezone
import bcrypt
import jwt

    
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

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
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token

def verify_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise {"message": "Token has expired"}
    except jwt.InvalidTokenError:
        raise {"message": "Invalid token"}