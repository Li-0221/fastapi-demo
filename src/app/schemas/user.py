from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import RqModel, RsModel

EmailField = Annotated[EmailStr, Field(max_length=255)]
NameField = Annotated[str | None, Field(max_length=255)]
PasswordField = Annotated[str, Field(min_length=8, max_length=128)]
# 不改变密码的校验或序列化, 只避免 Pydantic repr 暴露明文。
SensitivePasswordField = Annotated[PasswordField, Field(repr=False)]
OptionalPasswordField = Annotated[PasswordField | None, Field(repr=False)]


class UserRegisterRequest(RqModel):
    email: EmailField
    full_name: NameField = None
    password: SensitivePasswordField


class UserCreateRequest(RqModel):
    email: EmailField
    full_name: NameField = None
    password: SensitivePasswordField
    is_active: bool = True
    is_superuser: bool = False


class UserPutRequest(RqModel):
    email: EmailField
    full_name: NameField
    password: OptionalPasswordField = None
    is_active: bool
    is_superuser: bool


class UserSelfPutRequest(RqModel):
    email: EmailField
    full_name: NameField


class UserPasswordChangeRequest(RqModel):
    current_password: SensitivePasswordField
    new_password: SensitivePasswordField


class UserData(RsModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserListQuery(RqModel):
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20
