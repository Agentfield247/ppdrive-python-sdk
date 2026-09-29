from __future__ import annotations


class PPDriveError(Exception):
    """Base error for all PPDRIVE API failures."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status}, message={self.message!r})"


class ValidationError(PPDriveError):
    """400 — bad request parameters."""


class AuthenticationError(PPDriveError):
    """401 — invalid or missing credentials."""


class AuthorizationError(PPDriveError):
    """403 — insufficient permissions."""


class NotFoundError(PPDriveError):
    """404 — resource not found."""


class ConflictError(PPDriveError):
    """409 — resource already exists."""


class PayloadTooLargeError(PPDriveError):
    """413 — file too large."""


class RangeError(PPDriveError):
    """416 — invalid range header."""


class RateLimitError(PPDriveError):
    """429 — too many requests."""


class ServerError(PPDriveError):
    """500 — internal server error."""


STATUS_MAP: dict[int, type[PPDriveError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    409: ConflictError,
    413: PayloadTooLargeError,
    416: RangeError,
    429: RateLimitError,
    500: ServerError,
}


def error_for_status(status: int, message: str) -> PPDriveError:
    return STATUS_MAP.get(status, PPDriveError)(status, message)
