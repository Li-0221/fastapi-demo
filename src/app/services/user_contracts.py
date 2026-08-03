from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    full_name: str | None
    password: str


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    full_name: str | None
    password: str
    is_active: bool
    is_superuser: bool


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    email: str | None
    email_supplied: bool
    full_name: str | None
    full_name_supplied: bool
    password: str | None
    password_supplied: bool
    is_active: bool | None
    is_active_supplied: bool
    is_superuser: bool | None
    is_superuser_supplied: bool


@dataclass(frozen=True, slots=True)
class UserResult:
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UserPageResult:
    items: list[UserResult]
    total: int
    page: int
    page_size: int
