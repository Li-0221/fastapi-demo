from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


# 这些 command 会短暂持有明文密码; repr=False 只用于防止日志和调试输出泄漏。
@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    full_name: str | None
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    full_name: str | None
    password: str = field(repr=False)
    is_active: bool
    is_superuser: bool


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    email: str | None
    email_supplied: bool
    full_name: str | None
    full_name_supplied: bool
    password: str | None = field(repr=False)
    password_supplied: bool
    is_active: bool | None
    is_active_supplied: bool
    is_superuser: bool | None
    is_superuser_supplied: bool


# scope 表达“当前用户”或“管理员”用例; 真正的 actor/目标校验仍由 UserService 完成。
class UserManagementScope(Enum):
    CURRENT_USER = "current_user"
    ADMIN = "admin"


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
