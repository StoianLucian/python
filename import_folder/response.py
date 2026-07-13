from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")

class ToolResponse(BaseModel, Generic[T]):
    success: bool
    result: T