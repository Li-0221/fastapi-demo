from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status

from app.dependencies.auth import CurrentSuperuser, CurrentUser
from app.dependencies.user import UserServiceDep
from app.mappers.user import UserCommandMapper
from app.presenters.user import UserPresenter
from app.schemas.common import ApiResponse, PageData
from app.schemas.user import (
    UserCreateRequest,
    UserData,
    UserListQuery,
    UserPatchRequest,
    UserSelfPatchRequest,
)

router = APIRouter(prefix="/users", tags=["users"])
UserIdPath = Annotated[UUID, Path()]


@router.get("/me")
def get_current_user(current_user: CurrentUser) -> ApiResponse[UserData]:
    return ApiResponse(data=UserPresenter.detail(current_user))


@router.patch("/me")
def update_current_user(
    request: UserSelfPatchRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.update_user(
        actor_id=current_user.id,
        user_id=current_user.id,
        command=UserCommandMapper.self_patch(request),
        allow_self=True,
    )
    return ApiResponse(data=UserPresenter.detail(user))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    current_user: CurrentUser,
    service: UserServiceDep,
) -> Response:
    service.delete_user(
        actor_id=current_user.id,
        user_id=current_user.id,
        allow_self=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreateRequest,
    current_superuser: CurrentSuperuser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    del current_superuser
    user = service.create_user(UserCommandMapper.create(request))
    return ApiResponse(data=UserPresenter.detail(user))


@router.get("")
def list_users(
    query: Annotated[UserListQuery, Query()],
    current_superuser: CurrentSuperuser,
    service: UserServiceDep,
) -> ApiResponse[PageData[UserData]]:
    del current_superuser
    result = service.list_users(page=query.page, page_size=query.page_size)
    return ApiResponse(data=UserPresenter.page(result))


@router.get("/{user_id}")
def get_user(
    user_id: UserIdPath,
    current_superuser: CurrentSuperuser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    del current_superuser
    user = service.get_user(user_id)
    return ApiResponse(data=UserPresenter.detail(user))


@router.patch("/{user_id}")
def update_user(
    user_id: UserIdPath,
    request: UserPatchRequest,
    current_superuser: CurrentSuperuser,
    service: UserServiceDep,
) -> ApiResponse[UserData]:
    user = service.update_user(
        actor_id=current_superuser.id,
        user_id=user_id,
        command=UserCommandMapper.patch(request),
        allow_self=False,
    )
    return ApiResponse(data=UserPresenter.detail(user))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UserIdPath,
    current_superuser: CurrentSuperuser,
    service: UserServiceDep,
) -> Response:
    service.delete_user(
        actor_id=current_superuser.id,
        user_id=user_id,
        allow_self=False,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
