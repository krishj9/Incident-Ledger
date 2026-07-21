class ServiceError(Exception):
    """Base service exception."""
    pass


class UnauthorizedError(ServiceError):
    """Raised when an action is unauthorized for the user."""
    pass


class ValidationFailedError(ServiceError):
    """Raised when domain validation rules fail."""
    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


class InvalidStateError(ServiceError):
    """Raised when a state machine transition fails."""
    pass
