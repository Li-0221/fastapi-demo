from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class RqModel(CamelModel):
    # HTTP 入站只接受 alias(camelCase), 不把 Python 字段名当作备用 wire contract。
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=False,
    )


class RsModel(CamelModel):
    pass


class ApiResponse[DataT](RsModel):
    data: DataT


class PaginationQuery(RqModel):
    page: Annotated[int, Field(ge=1, le=10_000)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20


class PageData[DataT](RsModel):
    items: list[DataT]
    total: int
    page: int
    page_size: int


class MessageData(RsModel):
    message: str


class ValidationIssue(RsModel):
    location: list[str]
    message: str
    error_type: str


class ErrorData(RsModel):
    code: str
    message: str
    request_id: str
    details: tuple[ValidationIssue, ...]


class ErrorResponse(RsModel):
    error: ErrorData
