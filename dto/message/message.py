from typing import Optional

from pydantic import BaseModel


class CreateMessage(BaseModel):
    content: str
    role: str
    images: Optional[list[str]] = None
