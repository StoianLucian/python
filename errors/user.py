class AppError(Exception):
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class AccountAlreadyExistsError(AppError):
    def __init__(self):
        super().__init__(
            message="Account already exists",
            error_code="account_exists",
            status_code=409
        )


class ErrorDeletingUserError(AppError):
    def __init__(self):
        super().__init__(
            message="Error deleting user",
            error_code="delete_user_error",
            status_code=409
        )


class UserNotFoundError(AppError):
    def __init__(self):
        super().__init__(
            message="User not found",
            error_code="user_not_found",
            status_code=404
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


class PDFFileSupportedError(AppError):
    def __init__(self):
        super().__init__(
            message="Pdf only supported",
            error_code="pdf_type_supported",
            status_code=401
        )
