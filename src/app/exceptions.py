from enum import Enum
from http import HTTPStatus


class ErrorCode(Enum):
    business_code: int
    http_status: HTTPStatus
    default_message: str

    def __init__(
        self,
        business_code: int,
        http_status: HTTPStatus,
        default_message: str,
    ) -> None:
        self.business_code = business_code
        self.http_status = http_status
        self.default_message = default_message

    AUTHENTICATION_REQUIRED = (
        10001,
        HTTPStatus.UNAUTHORIZED,
        "Authentication is required",
    )
    INVALID_CREDENTIALS = (
        10002,
        HTTPStatus.UNAUTHORIZED,
        "Incorrect email or password",
    )
    INVALID_CURRENT_PASSWORD = (
        10003,
        HTTPStatus.BAD_REQUEST,
        "Current password is incorrect",
    )
    INACTIVE_USER = (
        10004,
        HTTPStatus.FORBIDDEN,
        "This user account is inactive",
    )
    PERMISSION_DENIED = (
        10005,
        HTTPStatus.FORBIDDEN,
        "You do not have permission to perform this action",
    )
    USER_NOT_FOUND = (
        10006,
        HTTPStatus.NOT_FOUND,
        "User not found",
    )
    EMAIL_ALREADY_EXISTS = (
        10007,
        HTTPStatus.CONFLICT,
        "A user with this email already exists",
    )
    SELF_ADMINISTRATION_NOT_ALLOWED = (
        10008,
        HTTPStatus.CONFLICT,
        "You cannot manage your own account through an administrator endpoint",
    )
    VALIDATION_ERROR = (
        10009,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "Request validation failed",
    )
    HTTP_ERROR = (
        10010,
        HTTPStatus.BAD_REQUEST,
        "HTTP request failed",
    )
    INTERNAL_ERROR = (
        10011,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "An unexpected error occurred",
    )


class AppError(Exception):
    code = ErrorCode.INTERNAL_ERROR


class AuthenticationRequiredError(AppError):
    code = ErrorCode.AUTHENTICATION_REQUIRED


class InvalidCredentialsError(AppError):
    code = ErrorCode.INVALID_CREDENTIALS


class InvalidCurrentPasswordError(AppError):
    code = ErrorCode.INVALID_CURRENT_PASSWORD


class InactiveUserError(AppError):
    code = ErrorCode.INACTIVE_USER


class PermissionDeniedError(AppError):
    code = ErrorCode.PERMISSION_DENIED


class UserNotFoundError(AppError):
    code = ErrorCode.USER_NOT_FOUND


class EmailAlreadyExistsError(AppError):
    code = ErrorCode.EMAIL_ALREADY_EXISTS


class SelfAdministrationError(AppError):
    code = ErrorCode.SELF_ADMINISTRATION_NOT_ALLOWED
