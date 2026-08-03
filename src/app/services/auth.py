from dataclasses import dataclass

from app.core.security import create_access_token, decode_access_token, verify_password
from app.db.session import DatabaseSessionManager
from app.exceptions import AuthenticationRequiredError, InactiveUserError, InvalidCredentialsError
from app.mappers.user_result import UserResultMapper
from app.repositories.user import UserRepository
from app.services.user_contracts import UserResult


@dataclass(frozen=True, slots=True)
class AccessTokenResult:
    access_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class LoginUserFacts:
    user: UserResult
    hashed_password: str


class AuthService:
    def __init__(
        self,
        *,
        manager: DatabaseSessionManager,
        secret_key: str,
        access_token_expire_minutes: int,
    ) -> None:
        self.manager = manager
        self.secret_key = secret_key
        self.access_token_expire_minutes = access_token_expire_minutes

    def login(self, *, email: str, password: str) -> AccessTokenResult:
        normalized_email = email.strip().casefold()
        with self.manager.session_scope() as session:
            user = UserRepository(session).get_by_email(normalized_email)
            if user is None:
                raise InvalidCredentialsError
            facts = LoginUserFacts(
                user=UserResultMapper.from_model(user),
                hashed_password=user.hashed_password,
            )

        if not verify_password(password, facts.hashed_password):
            raise InvalidCredentialsError
        if not facts.user.is_active:
            raise InactiveUserError

        access_token = create_access_token(
            subject=facts.user.id,
            secret_key=self.secret_key,
            expires_minutes=self.access_token_expire_minutes,
        )
        return AccessTokenResult(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60,
        )

    def authenticate_access_token(self, token: str) -> UserResult:
        claims = decode_access_token(token=token, secret_key=self.secret_key)
        if claims is None:
            raise AuthenticationRequiredError

        with self.manager.session_scope() as session:
            user = UserRepository(session).get_by_id(claims.sub)
            if user is None:
                raise AuthenticationRequiredError
            if not user.is_active:
                raise InactiveUserError
            return UserResultMapper.from_model(user)
