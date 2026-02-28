from __future__ import annotations


class DomainException(Exception):
    """Base domain exception."""
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class GeminiAPIError(DomainException):
    """SDK call failure."""
    status_code = 502
    detail = "Gemini API call failed"


class QuotaExceededError(DomainException):
    """Quota exceeded (429 from google.api_core)."""
    status_code = 429
    detail = "API quota exceeded. Please try again later."


class SafetyBlockError(DomainException):
    """Safety filter blocked the request."""
    status_code = 422
    detail = "Request blocked by safety filter"


class InvalidInputError(DomainException):
    """Invalid input validation."""
    status_code = 400
    detail = "Invalid input"
