class AppError(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)

class UsernameExistsError(AppError):
    def __init__(self):
        super().__init__(
            message="Username already exists",
            error_code="username_exists",
            status_code=409
        )


class EmailExistsError(AppError):
    def __init__(self):
        super().__init__(
            message="Email already exists",
            error_code="email_exists",
            status_code=409
        )
        
class NotAuthenticatedError(AppError):
    def __init__(self):
        super().__init__(
            message="Not authenticated",
            error_code="not_authenticated",
            status_code=401
        )
