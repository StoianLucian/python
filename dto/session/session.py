from pydantic import BaseModel


class CreateSession(BaseModel):
    query: str
