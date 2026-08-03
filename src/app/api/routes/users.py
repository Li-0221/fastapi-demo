from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status

from app.dependencies.auth import CurrentUser
from app.dependencies.user import UserServiceDep
from app.presenters.user import UserPresenter
from app.schemas.common import ApiResponse, PageData
from app.schemas.user import (
    UserCreateRequest,
    UserData,
    UserListQuery,
    UserPutRequest,
    UserSelfPutRequest,
)
from app.services.user_contracts import (
    CreateUserCommand,
    UpdateCurrentUserCommand,
    UpdateUserCommand,
)

router = APIRouter(prefix="/users", tags=["users"])
# 路由与 OpenAPI 使用 camelCase, 函数内部仍保留 Python 的 snake_case 命名。
UserIdPath = Annotated[UUID, Path(alias="userId")]


@router.get("/me")
def get_current_user(current_user: CurrentUser) -> ApiResponse[UserData]:
    return ApiResponse(data=UserPresenter.detail(current_user))


@router.put("/me")
def update_current_user(
    request: UserSelfPutRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.update_current_user(
        actor=current_user,
        command=UpdateCurrentUserCommand.from_request(request),
    )
    return ApiResponse(data=UserPresenter.detail(user))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreateRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.create_user_as_admin(
        actor=current_user,
        command=CreateUserCommand.from_request(request),
    )
    return ApiResponse(data=UserPresenter.detail(user))


@router.get("")
def list_users(
    query: Annotated[UserListQuery, Query()],
    current_user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[PageData[UserData]]:
    result = service.list_users(
        actor=current_user,
        page=query.page,
        page_size=query.page_size,
    )
    return ApiResponse(data=UserPresenter.page(result))


@router.get("/{userId}")
def get_user(
    user_id: UserIdPath,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.get_user(actor=current_user, user_id=user_id)
    return ApiResponse(data=UserPresenter.detail(user))


@router.put("/{userId}")
def update_user(
    user_id: UserIdPath,
    request: UserPutRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.update_user_as_admin(
        actor=current_user,
        user_id=user_id,
        command=UpdateUserCommand.from_request(request),
    )
    return ApiResponse(data=UserPresenter.detail(user))


@router.delete("/{userId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UserIdPath,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> Response:
    service.delete_user(
        actor=current_user,
        user_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
