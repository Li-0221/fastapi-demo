from uuid import UUID

from app.core.security import hash_password
from app.db.session import DatabaseSessionManager
from app.exceptions import (
    EmailAlreadyExistsError,
    SelfAdministrationError,
    SuperuserSelfDeleteError,
    UserNotFoundError,
)
from app.mappers.user_result import UserResultMapper
from app.repositories.user import (
    DuplicateUserRecordError,
    UserRecordCreate,
    UserRecordUpdate,
    UserRepository,
)
from app.services.user_contracts import (
    CreateUserCommand,
    RegisterUserCommand,
    UpdateUserCommand,
    UserPageResult,
    UserResult,
)


class UserService:
    def __init__(self, *, manager: DatabaseSessionManager) -> None:
        self.manager = manager

    def register_user(self, command: RegisterUserCommand) -> UserResult:
        return self.create_user(
            CreateUserCommand(
                email=command.email,
                full_name=command.full_name,
                password=command.password,
                is_active=True,
                is_superuser=False,
            )
        )

    def create_user(self, command: CreateUserCommand) -> UserResult:
        record = UserRecordCreate(
            email=command.email.strip().casefold(),
            full_name=command.full_name,
            hashed_password=hash_password(command.password),
            is_active=command.is_active,
            is_superuser=command.is_superuser,
        )
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            try:
                user = repository.create(record)
                session.commit()
            except DuplicateUserRecordError:
                session.rollback()
                raise EmailAlreadyExistsError from None
            return UserResultMapper.from_model(user)

    def get_user(self, user_id: UUID) -> UserResult:
        with self.manager.session_scope() as session:
            user = UserRepository(session).get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            return UserResultMapper.from_model(user)

    def list_users(self, *, page: int, page_size: int) -> UserPageResult:
        with self.manager.session_scope() as session:
            items, total = UserRepository(session).list_page(
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return UserPageResult(
                items=[UserResultMapper.from_model(user) for user in items],
                total=total,
                page=page,
                page_size=page_size,
            )

    def update_user(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        command: UpdateUserCommand,
        allow_self: bool,
    ) -> UserResult:
        if actor_id == user_id and not allow_self:
            raise SelfAdministrationError

        hashed_password = None
        if command.password_supplied and command.password is not None:
            hashed_password = hash_password(command.password)
        record = UserRecordUpdate(
            email=command.email.strip().casefold() if command.email is not None else None,
            email_supplied=command.email_supplied,
            full_name=command.full_name,
            full_name_supplied=command.full_name_supplied,
            hashed_password=hashed_password,
            password_supplied=command.password_supplied,
            is_active=command.is_active,
            is_active_supplied=command.is_active_supplied,
            is_superuser=command.is_superuser,
            is_superuser_supplied=command.is_superuser_supplied,
        )
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            try:
                repository.update(user=user, data=record)
                session.commit()
            except DuplicateUserRecordError:
                session.rollback()
                raise EmailAlreadyExistsError from None
            return UserResultMapper.from_model(user)

    def delete_user(
        self,
        *,
        actor_id: UUID,
        user_id: UUID,
        allow_self: bool,
    ) -> None:
        if actor_id == user_id and not allow_self:
            raise SelfAdministrationError

        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            if actor_id == user_id and user.is_superuser:
                raise SuperuserSelfDeleteError
            repository.delete(user)
            session.commit()
