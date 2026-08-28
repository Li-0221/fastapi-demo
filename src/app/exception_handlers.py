import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.exceptions import AppError, ErrorCode
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def error_json_response(
    *,
    status_code: int,
    code: ErrorCode,
    request_id: str,
    message: str | None = None,
) -> JSONResponse:
    response = ErrorResponse(
        code=code.business_code,
        message=message if message is not None else code.default_message,
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
        status_code=error.code.http_status,
        code=error.code,
        request_id=request.state.request_id,
        message=error.code.default_message,
    )


async def handle_request_validation(
    request: Request,
    _error: RequestValidationError,
) -> JSONResponse:
    return error_json_response(
        status_code=ErrorCode.VALIDATION_ERROR.http_status,
        code=ErrorCode.VALIDATION_ERROR,
        request_id=request.state.request_id,
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
        code=ErrorCode.HTTP_ERROR,
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
        status_code=ErrorCode.INTERNAL_ERROR.http_status,
        code=ErrorCode.INTERNAL_ERROR,
        request_id=request.state.request_id,
    )
