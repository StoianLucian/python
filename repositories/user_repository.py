from datetime import datetime
from db.schemas.user import User
from errors.user import UserNotFoundError
from services import check_match_password, hash_password, check_existing_user
from sqlalchemy.orm import Session, load_only
from schemas import UserCreate
import logging


def create_user_db(userData: UserCreate, db: Session):
    check_match_password(userData.password, userData.confirmPassword)
    check_existing_user(userData, db)

    user = User(
        username=userData.username,
        email=userData.email,
        password=hash_password(userData.password),
        created_at=datetime.now()
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id


def get_all_users_db(db: Session):

    users = db.query(User).options(
        load_only(User.id, User.username, User.email)).all()
    logging.info(f"user_repository.get_all_users_db")
    return users


def get_user_by_id_db(id: int, db: Session):

    logging.info(f"user_repository.get_user_by_id_db {id}")
    user = db.query(User).options(
        load_only(User.id, User.username, User.email)
    ).filter(User.id == id).first()

    if user is None:
        raise UserNotFoundError()

    return user


def delete_user_by_id_db(id: int, db: Session) -> bool:
    logging.info(f"auth.delete_user_by_id_db {id}")
    user = get_user_by_id_db(id, db)

    db.delete(user)
    db.commit()

    return True
