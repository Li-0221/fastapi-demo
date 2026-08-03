class AppError(Exception):
    code = "APP_ERROR"
    message = "Application error"
    status_code = 500


class AuthenticationRequiredError(AppError):
    code = "AUTHENTICATION_REQUIRED"
    message = "Authentication is required"
    status_code = 401


class InvalidCredentialsError(AppError):
    code = "INVALID_CREDENTIALS"
    message = "Incorrect email or password"
    status_code = 401


class InactiveUserError(AppError):
    code = "INACTIVE_USER"
    message = "This user account is inactive"
    status_code = 403


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"
    status_code = 403


class UserNotFoundError(AppError):
    code = "USER_NOT_FOUND"
    message = "User not found"
    status_code = 404


class EmailAlreadyExistsError(AppError):
    code = "EMAIL_ALREADY_EXISTS"
    message = "A user with this email already exists"
    status_code = 409


class SelfAdministrationError(AppError):
    code = "SELF_ADMINISTRATION_NOT_ALLOWED"
    message = "You cannot manage your own account through an administrator endpoint"
    status_code = 409
