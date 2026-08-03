from typing import Any

from app.schemas.common import ErrorResponse

# tripguru-ast: ignore[TG-DS001] - FastAPI owns the OpenAPI responses mapping protocol
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    # tripguru-ast: ignore[TG-DS001] - FastAPI owns this response metadata mapping
    401: {"model": ErrorResponse},
    # tripguru-ast: ignore[TG-DS001] - FastAPI owns this response metadata mapping
    403: {"model": ErrorResponse},
    # tripguru-ast: ignore[TG-DS001] - FastAPI owns this response metadata mapping
    404: {"model": ErrorResponse},
    # tripguru-ast: ignore[TG-DS001] - FastAPI owns this response metadata mapping
    409: {"model": ErrorResponse},
    # tripguru-ast: ignore[TG-DS001] - FastAPI owns this response metadata mapping
    422: {"model": ErrorResponse},
    # tripguru-ast: ignore[TG-DS001] - FastAPI owns this response metadata mapping
    500: {"model": ErrorResponse},
}
