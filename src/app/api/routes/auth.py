from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies.auth import AuthServiceDep
from app.dependencies.user import UserServiceDep
from app.presenters.user import UserPresenter
from app.schemas.auth import AccessTokenResponse
from app.schemas.common import ApiResponse
from app.schemas.user import UserData, UserRegisterRequest
from app.services.user_contracts import RegisterUserCommand

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    request: UserRegisterRequest,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.register_user(RegisterUserCommand.from_request(request))
    return ApiResponse(data=UserPresenter.detail(user))


@router.post("/login/access-token")
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> AccessTokenResponse:
    result = service.login(email=form_data.username, password=form_data.password)
    return AccessTokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
    )
