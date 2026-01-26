from enum import Enum

class UserErrorCode(str, Enum):
    USER_NOT_FOUND = "user_not_found"