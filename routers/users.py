from fastapi import APIRouter, Depends, HTTPException
from schemas import *
from helpers.helpers import raise_error
from sqlalchemy.orm import Session

from repositories import *

router = APIRouter(
    prefix="/users",
    tags=["users"],

)


@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        created_user = create_user_db(user, db)

        return created_user
    except Exception as e:
        raise e


@router.get("/", response_model=list[UserRead], )
def get_all_users(user=Depends(check_token), db: Session = Depends(get_db)):
    try:
        users = get_all_users_db(db)
        return users
    except Exception as e:
        raise e


@router.get("/{id}")
def get_user_by_id(id, db: Session = Depends(get_db), user=Depends(check_token)):
    try:
        user = get_user_by_id_db(id, db)
        return user
    except Exception as e:
        raise e


@router.delete("/{id}")
def delete_user_by_id(id: int, db: Session = Depends(get_db)):
    try:
        success = delete_user_by_id_db(id, db)
        if not success:
            raise UserNotFoundError()

        return "user deleted"
    except HTTPException as e:
        # forward HTTPException exact așa cum este
        raise e
