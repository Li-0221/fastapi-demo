from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import UUID

from app.models.user import User
from app.schemas.user import (
    UserCreateRequest,
    UserPutRequest,
    UserRegisterRequest,
    UserSelfPutRequest,
)


# 这些 command 会短暂持有明文密码; repr=False 只用于防止日志和调试输出泄漏。
@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    full_name: str | None
    password: str = field(repr=False)

    @classmethod
    def from_request(cls, request: UserRegisterRequest) -> Self:
        return cls(
            email=str(request.email),
            full_name=request.full_name,
            password=request.password,
        )


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    full_name: str | None
    password: str = field(repr=False)
    is_active: bool
    is_superuser: bool

    @classmethod
    def from_request(cls, request: UserCreateRequest) -> Self:
        return cls(
            email=str(request.email),
            full_name=request.full_name,
            password=request.password,
            is_active=request.is_active,
            is_superuser=request.is_superuser,
        )


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserCommand:
    email: str
    full_name: str | None
    password: str | None = field(repr=False)

    @classmethod
    def from_request(cls, request: UserSelfPutRequest) -> Self:
        return cls(
            email=str(request.email),
            full_name=request.full_name,
            password=request.password,
        )


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    email: str
    full_name: str | None
    password: str | None = field(repr=False)
    is_active: bool
    is_superuser: bool

    @classmethod
    def from_request(cls, request: UserPutRequest) -> Self:
        return cls(
            email=str(request.email),
            full_name=request.full_name,
            password=request.password,
            is_active=request.is_active,
            is_superuser=request.is_superuser,
        )


@dataclass(frozen=True, slots=True)
class UserResult:
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user: User) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


@dataclass(frozen=True, slots=True)
class UserPageResult:
    items: list[UserResult]
    total: int
    page: int
    page_size: int
