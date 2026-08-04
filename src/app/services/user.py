from uuid import UUID

from app.core.security import hash_password, verify_password
from app.db.session import DatabaseSessionManager
from app.exceptions import (
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
    PermissionDeniedError,
    SelfAdministrationError,
    UserNotFoundError,
)
from app.repositories.user import (
    DuplicateUserRecordError,
    UserPasswordChange,
    UserRecordCreate,
    UserRecordReplacement,
    UserRepository,
)
from app.services.user_contracts import (
    ChangeCurrentUserPasswordCommand,
    CreateUserCommand,
    RegisterUserCommand,
    UpdateCurrentUserCommand,
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
            return UserResult.from_model(user)

    # 管理用例由 Service 再次校验 actor, 不能只依赖 Router 是否隐藏或暴露入口。
    def create_user_as_admin(
        self,
        *,
        actor: UserResult,
        command: CreateUserCommand,
    ) -> UserResult:
        if not actor.is_superuser:
            raise PermissionDeniedError
        return self.create_user(command)

    def get_user(self, *, actor: UserResult, user_id: UUID) -> UserResult:
        if not actor.is_superuser:
            raise PermissionDeniedError
        with self.manager.session_scope() as session:
            user = UserRepository(session).get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            return UserResult.from_model(user)

    def list_users(
        self,
        *,
        actor: UserResult,
        page: int,
        page_size: int,
    ) -> UserPageResult:
        if not actor.is_superuser:
            raise PermissionDeniedError
        with self.manager.session_scope() as session:
            items, total = UserRepository(session).list_page(
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return UserPageResult(
                items=[UserResult.from_model(user) for user in items],
                total=total,
                page=page,
                page_size=page_size,
            )

    def update_current_user(
        self,
        *,
        actor: UserResult,
        command: UpdateCurrentUserCommand,
    ) -> UserResult:
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(actor.id)
            if user is None:
                raise UserNotFoundError
            record = UserRecordReplacement(
                email=command.email.strip().casefold(),
                full_name=command.full_name,
                hashed_password=None,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
            )
            try:
                repository.replace(user=user, data=record)
                session.commit()
            except DuplicateUserRecordError:
                session.rollback()
                raise EmailAlreadyExistsError from None
            return UserResult.from_model(user)

    def change_current_user_password(
        self,
        *,
        actor: UserResult,
        command: ChangeCurrentUserPasswordCommand,
    ) -> None:
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id_for_update(actor.id)
            if user is None:
                raise UserNotFoundError
            if not verify_password(command.current_password, user.hashed_password):
                raise InvalidCurrentPasswordError
            repository.change_password(
                user=user,
                data=UserPasswordChange(hashed_password=hash_password(command.new_password)),
            )
            session.commit()

    def update_user_as_admin(
        self,
        *,
        actor: UserResult,
        user_id: UUID,
        command: UpdateUserCommand,
    ) -> UserResult:
        if not actor.is_superuser:
            raise PermissionDeniedError
        if actor.id == user_id:
            raise SelfAdministrationError

        hashed_password = hash_password(command.password) if command.password is not None else None
        record = UserRecordReplacement(
            email=command.email.strip().casefold(),
            full_name=command.full_name,
            hashed_password=hashed_password,
            is_active=command.is_active,
            is_superuser=command.is_superuser,
        )
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            try:
                repository.replace(user=user, data=record)
                session.commit()
            except DuplicateUserRecordError:
                session.rollback()
                raise EmailAlreadyExistsError from None
            return UserResult.from_model(user)

    def delete_user(
        self,
        *,
        actor: UserResult,
        user_id: UUID,
    ) -> None:
        # 删除用户只属于管理员用例, 并且管理员不能通过管理端点删除自己。
        if not actor.is_superuser:
            raise PermissionDeniedError
        if actor.id == user_id:
            raise SelfAdministrationError

        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            repository.delete(user)
            session.commit()
