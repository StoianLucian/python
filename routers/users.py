from fastapi import APIRouter, HTTPException
from schemas.user_schemas import UserCreate, UserRead
from helpers.helpers import raise_error

from errors import UserErrorCode
from repositories import *


router = APIRouter(prefix="/users", tags=["users"])

@router.post("/")
def create_user(user: UserCreate):
    try:
        created_user = create_user_db(user)
        return created_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/", response_model=list[UserRead])
def get_all_users():
    try: 
        users = get_all_users_db()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/{id}")
def get_user_by_id(id):
    try:
        user = get_user_by_id_db(id)
        return user
    except Exception as e:
        raise HTTPException(500, str(e))

    
@router.delete("/{id}")
def delete_user_by_id(id: int):
    try:
        success = delete_user_by_id_db(id)
        if not success:
            raise raise_error(404, f"user with id {id} not found", UserErrorCode.USER_NOT_FOUND)
    except HTTPException as e:
        # forward HTTPException exact așa cum este
        raise e
    except Exception as e:
        # alte erori neașteptate
        raise HTTPException(
            status_code=500,
            detail={"message": str(e), "code": "internal_error"}
        )