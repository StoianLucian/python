from errors.user import AppError


class SummaryNotCreatedError(AppError):
    def __init__(self):
        super().__init__(
            message="Summary not created",
            error_code="summary_not_created",
            status_code=403
        )