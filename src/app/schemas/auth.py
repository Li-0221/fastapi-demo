from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AccessTokenResponse(BaseModel):
    # token 仍会按 OAuth2 契约序列化返回; repr=False 仅避免调试输出意外泄漏。
    access_token: Annotated[str, Field(repr=False)]
    # 使用 Literal 防止业务代码构造非标准 token type。
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
