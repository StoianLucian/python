from pydantic import BaseModel


class CreateMessage(BaseModel):
    content: str
    role: str
