from typing import Generic, TypeVar
from pydantic import BaseModel, Field

# Generic type variable for API responses
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Generic API response wrapper.

    Used for all RAGFlow API responses that follow the standard format:
    {"code": 0, "message": "", "data": {...}}
    """

    code: int = Field(..., description="Response code (0 for success)")
    message: str = Field(default="", description="Error message if code != 0")
    data: T | None = Field(None, description="Response data")

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.code == 0

    def raise_for_status(self):
        """Raise an exception if the response indicates an error."""
        from ..exceptions import RagFlowAPIError

        if not self.is_success:
            raise RagFlowAPIError(
                message=self.message or f"API error (code {self.code})",
                error_code=str(self.code),
                response_data=self.model_dump(),
            )


class Paginated(BaseModel, Generic[T]):
    """
    Generic paginated response.

    Used for list endpoints that return paginated results.
    """

    items: list[T] = Field(default_factory=list, description="List of items")
    total: int = Field(0, description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of items per page")

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page * self.page_size < self.total

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
