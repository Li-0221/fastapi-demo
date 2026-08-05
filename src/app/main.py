from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_app_settings, get_database_settings
from app.dependencies.database import get_database_manager
from app.exception_handlers import (
    handle_app_error,
    handle_http_error,
    handle_request_validation,
    handle_unexpected_error,
)
from app.exceptions import AppError
from app.middleware import RequestIdMiddleware
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


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    manager = get_database_manager()
    try:
        yield
    finally:
        try:
            manager.dispose()
        finally:
            get_database_manager.cache_clear()


def create_app() -> FastAPI:
    settings = get_app_settings()
    # 在启动边界校验必填数据库配置, 但不连接数据库, 也不自动执行 migration。
    get_database_settings()
    application = FastAPI(
        title=settings.name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        responses=ERROR_RESPONSES,
        lifespan=application_lifespan,
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]
    application.add_exception_handler(
        RequestValidationError,
        handle_request_validation,  # type: ignore[arg-type]
    )
    application.add_exception_handler(
        StarletteHTTPException,
        handle_http_error,  # type: ignore[arg-type]
    )
    application.add_exception_handler(Exception, handle_unexpected_error)
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
