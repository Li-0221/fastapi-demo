from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from app.schemas.common import RqModel, RsModel

EmailField = Annotated[EmailStr, Field(max_length=255)]
NameField = Annotated[str | None, Field(max_length=255)]
PasswordField = Annotated[str, Field(min_length=8, max_length=128)]
NULL_EMAIL_MESSAGE = "email cannot be null"
NULL_PASSWORD_MESSAGE = "password cannot be null"
NULL_ACTIVE_MESSAGE = "is_active cannot be null"
NULL_SUPERUSER_MESSAGE = "is_superuser cannot be null"


class UserRegisterRequest(RqModel):
    email: EmailField
    full_name: NameField = None
    password: PasswordField


class UserCreateRequest(RqModel):
    email: EmailField
    full_name: NameField = None
    password: PasswordField
    is_active: bool = True
    is_superuser: bool = False


class UserPatchRequest(RqModel):
    email: EmailField | None = None
    full_name: NameField = None
    password: PasswordField | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None

    @model_validator(mode="after")
    def reject_null_for_non_nullable_fields(self) -> Self:
        if "email" in self.model_fields_set and self.email is None:
            raise ValueError(NULL_EMAIL_MESSAGE)
        if "password" in self.model_fields_set and self.password is None:
            raise ValueError(NULL_PASSWORD_MESSAGE)
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError(NULL_ACTIVE_MESSAGE)
        if "is_superuser" in self.model_fields_set and self.is_superuser is None:
            raise ValueError(NULL_SUPERUSER_MESSAGE)
        return self


class UserSelfPatchRequest(RqModel):
    email: EmailField | None = None
    full_name: NameField = None
    password: PasswordField | None = None

    @model_validator(mode="after")
    def reject_null_for_non_nullable_fields(self) -> Self:
        if "email" in self.model_fields_set and self.email is None:
            raise ValueError(NULL_EMAIL_MESSAGE)
        if "password" in self.model_fields_set and self.password is None:
            raise ValueError(NULL_PASSWORD_MESSAGE)
        return self


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
