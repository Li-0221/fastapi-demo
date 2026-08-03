from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BeforeValidator, EmailStr, Field
from pydantic.json_schema import JsonSchemaValue, SkipJsonSchema

from app.schemas.common import RqModel, RsModel

EmailField = Annotated[EmailStr, Field(max_length=255)]
NameField = Annotated[str | None, Field(max_length=255)]
PasswordField = Annotated[str, Field(min_length=8, max_length=128)]
# 不改变密码的校验或序列化, 只避免 Pydantic repr 暴露明文。
SensitivePasswordField = Annotated[PasswordField, Field(repr=False)]
NULL_PATCH_FIELD_MESSAGE = "field cannot be null"


def reject_explicit_null(value: object) -> object:
    # 默认 None 表示字段未提供; 只有请求显式传 null 时才会执行该 validator。
    if value is None:
        raise ValueError(NULL_PATCH_FIELD_MESSAGE)
    return value


def remove_omitted_default(schema: JsonSchemaValue) -> None:
    # Pydantic 内部需要 default=None 表示省略, 但公开 OpenAPI 不能宣称非空字段默认是 null。
    # tripguru-ast: ignore[TG-DS003] - 这是 Pydantic 拥有的 JSON Schema 动态映射边界
    schema.pop("default", None)


# 运行时由 None + model_fields_set 表达“省略”; SkipJsonSchema 防止 OpenAPI 把非空字段标成 nullable。
PatchEmailField = Annotated[
    EmailField | SkipJsonSchema[None],
    BeforeValidator(reject_explicit_null),
    Field(validate_default=False, json_schema_extra=remove_omitted_default),
]
PatchPasswordField = Annotated[
    PasswordField | SkipJsonSchema[None],
    BeforeValidator(reject_explicit_null),
    Field(
        validate_default=False,
        repr=False,
        json_schema_extra=remove_omitted_default,
    ),
]
PatchBooleanField = Annotated[
    bool | SkipJsonSchema[None],
    BeforeValidator(reject_explicit_null),
    Field(validate_default=False, json_schema_extra=remove_omitted_default),
]


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


class UserPatchRequest(RqModel):
    email: PatchEmailField = None
    # full_name 是唯一允许显式 null 清空的资料字段, 因此保留普通 Optional 契约。
    full_name: NameField = None
    password: PatchPasswordField = None
    is_active: PatchBooleanField = None
    is_superuser: PatchBooleanField = None


class UserSelfPatchRequest(RqModel):
    email: PatchEmailField = None
    full_name: NameField = None
    password: PatchPasswordField = None


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
