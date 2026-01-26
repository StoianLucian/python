from fastapi import HTTPException
from enum import Enum

def raise_error(status: int, message: str, code: Enum):
    raise HTTPException(
        status_code=status,
        detail={
            "message": message,
            "code": code.value
        }
    )