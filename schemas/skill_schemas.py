from datetime import date

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1)
    key: str = Field(..., min_length=1)


class SkillRead(BaseModel):
    id: int
    name: str
    key: str
    created_at: date
