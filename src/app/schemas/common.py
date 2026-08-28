from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class RequestModel(CamelModel):
    # HTTP 入站只接受 alias(camelCase), 不把 Python 字段名当作备用 wire contract。
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=False,
    )


class ResponseModel(CamelModel):
    pass


class ApiResponse[DataT](ResponseModel):
    code: Literal[0] = 0
    data: DataT
    message: Literal["success"] = "success"


class PaginationQuery(RequestModel):
    page: Annotated[int, Field(ge=1, le=10_000)] = 1
    page_size: Annotated[int, Field(alias="pagesize", ge=1, le=100)] = 20


class PageData[DataT](ResponseModel):
    total: int
    items: list[DataT]
    page: int
    page_size: Annotated[int, Field(serialization_alias="page_size")]


class ErrorResponse(ResponseModel):
    code: Annotated[int, Field(gt=0)]
    data: None = None
    message: str
