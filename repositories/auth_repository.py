from sql import LOGIN_USER
from context.context_manager import db_cursor

def login_user_db(userInfo):
    with db_cursor() as (_, cursor):
        cursor.execute(LOGIN_USER, (userInfo.username,))
        
        user = cursor.fetchone()
        if user is None:
            raise {"message": "user not found"}
        return user