from services import check_match_password, hash_password, check_existing_user
from sql import CREATE_USER, GET_ALL_USERS, DELETE_USER_BY_ID, GET_USER_BY_ID
from fastapi import HTTPException 

from context.context_manager import db_cursor
from schemas import UserCreate

def create_user_db(userData:UserCreate):
    with db_cursor() as (_, cursor):  # <-- ai nevoie de ()
        check_match_password(userData.password, userData.confirmPassword)
        check_existing_user(userData, cursor)
        
        password = hash_password(userData.password)

        cursor.execute(
            CREATE_USER,
            (userData.username, userData.email, password)
        )
        
        return cursor.fetchone()[0]

def get_all_users_db():
    with db_cursor() as (_, cursor):
        cursor.execute(GET_ALL_USERS)
        users = cursor.fetchall()
        return users
        
def get_user_by_id_db(id: int):
    with db_cursor(cursor_type="dict") as (_, cursor):
        cursor.execute(GET_USER_BY_ID, (id,))
        user = cursor.fetchone()
        
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "User not found",
                    "errorCode": "user_not_found"
                })
        
        return user
        
def delete_user_by_id_db(id: int) -> bool:
    with db_cursor() as (_, cursor):
        cursor.execute(DELETE_USER_BY_ID, (id,))
        return cursor.rowcount > 0