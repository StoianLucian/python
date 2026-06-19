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

def split_text(text, chunk_size=50):
    text = text.strip()
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
