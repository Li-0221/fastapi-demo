from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.openapi import ERROR_RESPONSES
from app.api.router import api_router
from app.core.config import get_app_settings
from app.exception_handlers import (
    handle_app_error,
    handle_http_error,
    handle_request_validation,
    handle_unexpected_error,
)
from app.exceptions import AppError
from app.middleware import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_app_settings()
    application = FastAPI(
        title=settings.name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        responses=ERROR_RESPONSES,
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
