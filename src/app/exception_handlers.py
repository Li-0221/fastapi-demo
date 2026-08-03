import logging
from typing import Annotated

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.exceptions import AppError
from app.schemas.common import ErrorData, ErrorResponse, ValidationIssue

logger = logging.getLogger(__name__)


class FrameworkValidationError(BaseModel):
    loc: tuple[str | int, ...]
    msg: str
    type: str
    input: Annotated[object | None, Field(exclude=True)] = None


def error_json_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: list[ValidationIssue] | None = None,
) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorData(
            code=code,
            message=message,
            request_id=request_id,
            details=tuple(details) if details is not None else (),
        )
    )
    # This is the actual JSON serialization boundary expected by Starlette.
    content = response.model_dump(mode="json", by_alias=True)
    # tripguru-ast: ignore[TG-DS001] - Starlette response headers are a mapping boundary
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    return error_json_response(
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        request_id=request.state.request_id,
    )


async def handle_request_validation(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    framework_errors = [FrameworkValidationError.model_validate(item) for item in error.errors()]
    details = [
        ValidationIssue(
            location=[str(part) for part in item.loc],
            message=item.msg,
            error_type=item.type,
        )
        for item in framework_errors
    ]
    return error_json_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=request.state.request_id,
        details=details,
    )


async def handle_http_error(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    message = "HTTP request failed"
    if error.status_code == 404:
        message = "Resource not found"
    if error.status_code == 405:
        message = "Method not allowed"
    return error_json_response(
        status_code=error.status_code,
        code="HTTP_ERROR",
        message=message,
        request_id=request.state.request_id,
    )


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_request_error",
        extra={  # tripguru-ast: ignore[TG-DS001] - logging extra is a mapping boundary
            "request_id": request.state.request_id,
            "path": request.url.path,
            "error_type": type(error).__name__,
        },
    )
    return error_json_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        request_id=request.state.request_id,
    )
