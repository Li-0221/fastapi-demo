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
    # 这里才是真正交给 Starlette 的 JSON 序列化边界, 因此显式使用公开 alias。
    content = response.model_dump(mode="json", by_alias=True)
    json_response = JSONResponse(status_code=status_code, content=content)
    # 未处理异常由最外层错误中间件生成响应, 可能绕过 RequestIdMiddleware 的返回路径。
    json_response.headers["X-Request-ID"] = request_id
    if status_code == 401:
        json_response.headers["WWW-Authenticate"] = "Bearer"
    return json_response


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
    response = error_json_response(
        status_code=error.status_code,
        code="HTTP_ERROR",
        message=message,
        request_id=request.state.request_id,
    )
    if error.headers is not None:
        # 只恢复 HTTP 协议必需的安全 header, 避免把框架异常中的任意 header 整包透传。
        for header_name, header_value in error.headers.items():
            if header_name.lower() in {"allow", "www-authenticate"}:
                response.headers[header_name] = header_value
    return response


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
