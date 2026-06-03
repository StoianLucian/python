from pydantic import BaseModel


class CreateSession(BaseModel):
    query: str
    
class UpdateSession(BaseModel):
    title: str
