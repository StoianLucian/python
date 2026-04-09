from pydantic import BaseModel


class LoginRequest(BaseModel):
    account: str
    password: str
