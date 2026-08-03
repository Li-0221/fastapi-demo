from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.config import get_app_settings
from app.dependencies.database import DatabaseManagerDep
from app.exceptions import AuthenticationRequiredError, PermissionDeniedError
from app.services.auth import AuthService
from app.services.user_contracts import UserResult

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_app_settings().api_v1_prefix}/auth/login/access-token",
    auto_error=False,
)


def get_auth_service(manager: DatabaseManagerDep) -> AuthService:
    settings = get_app_settings()
    return AuthService(
        manager=manager,
        secret_key=settings.secret_key.get_secret_value(),
        access_token_expire_minutes=settings.access_token_expire_minutes,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    auth_service: AuthServiceDep,
) -> UserResult:
    if token is None:
        raise AuthenticationRequiredError
    return auth_service.authenticate_access_token(token)


CurrentUser = Annotated[UserResult, Depends(get_current_user)]


def get_current_superuser(current_user: CurrentUser) -> UserResult:
    if not current_user.is_superuser:
        raise PermissionDeniedError
    return current_user


CurrentSuperuser = Annotated[UserResult, Depends(get_current_superuser)]
