from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, ValidationError, field_serializer

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


class AccessTokenClaims(BaseModel):
    sub: UUID
    exp: datetime
    iat: datetime
    type: Literal["access"]

    @field_serializer("exp", "iat", when_used="json")
    def serialize_numeric_date(self, value: datetime) -> int:
        return int(value.timestamp())


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(*, subject: UUID, secret_key: str, expires_minutes: int) -> str:
    issued_at = datetime.now(UTC)
    claims = AccessTokenClaims(
        sub=subject,
        exp=issued_at + timedelta(minutes=expires_minutes),
        iat=issued_at,
        type="access",
    )
    return jwt.encode(
        claims.model_dump(mode="json"),
        secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(*, token: str, secret_key: str) -> AccessTokenClaims | None:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        claims = AccessTokenClaims.model_validate(payload)
    except (InvalidTokenError, ValidationError):
        return None

    return claims
