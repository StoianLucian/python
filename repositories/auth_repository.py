from sql import LOGIN_USER
import jwt
from context.context_manager import db_cursor
from datetime import datetime, timedelta, timezone


def login_user_db(userInfo):
    with db_cursor() as (_, cursor):
        cursor.execute(LOGIN_USER, (userInfo.username,))
        
        user = cursor.fetchone()
        if user is None:
            raise {"message": "user not found"}
        return user
    
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
    
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