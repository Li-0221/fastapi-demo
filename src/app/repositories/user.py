from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


class DuplicateUserRecordError(Exception):
    """Raised when a database uniqueness constraint rejects a user write."""


class InvalidUserRecordUpdateError(Exception):
    """Raised when an internal update contract violates its supplied-value invariant."""


@dataclass(frozen=True, slots=True)
class UserRecordCreate:
    email: str
    full_name: str | None
    hashed_password: str
    is_active: bool
    is_superuser: bool


@dataclass(frozen=True, slots=True)
class UserRecordUpdate:
    email: str | None
    email_supplied: bool
    full_name: str | None
    full_name_supplied: bool
    hashed_password: str | None
    password_supplied: bool
    is_active: bool | None
    is_active_supplied: bool
    is_superuser: bool | None
    is_superuser_supplied: bool


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.scalar(statement)

    def list_page(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        statement = select(User).order_by(User.created_at.desc(), User.id.desc())
        count_statement = select(func.count()).select_from(User)
        items = list(self.session.scalars(statement.offset(offset).limit(limit)).all())
        total = self.session.scalar(count_statement) or 0
        return items, total

    def create(self, data: UserRecordCreate) -> User:
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=data.hashed_password,
            is_active=data.is_active,
            is_superuser=data.is_superuser,
        )
        self.session.add(user)
        try:
            self.session.flush()
        except IntegrityError as error:
            raise DuplicateUserRecordError from error
        return user

    def update(self, *, user: User, data: UserRecordUpdate) -> User:
        if data.email_supplied:
            if data.email is None:
                raise InvalidUserRecordUpdateError
            user.email = data.email
        if data.full_name_supplied:
            user.full_name = data.full_name
        if data.password_supplied:
            if data.hashed_password is None:
                raise InvalidUserRecordUpdateError
            user.hashed_password = data.hashed_password
        if data.is_active_supplied:
            if data.is_active is None:
                raise InvalidUserRecordUpdateError
            user.is_active = data.is_active
        if data.is_superuser_supplied:
            if data.is_superuser is None:
                raise InvalidUserRecordUpdateError
            user.is_superuser = data.is_superuser

        try:
            self.session.flush()
        except IntegrityError as error:
            raise DuplicateUserRecordError from error
        return user

    def delete(self, user: User) -> None:
        self.session.delete(user)
        self.session.flush()
