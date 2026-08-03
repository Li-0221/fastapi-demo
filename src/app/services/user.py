from uuid import UUID

from app.core.security import hash_password
from app.db.session import DatabaseSessionManager
from app.exceptions import (
    EmailAlreadyExistsError,
    PermissionDeniedError,
    SelfAdministrationError,
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
    UserManagementScope,
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
            return UserResultMapper.from_model(user)

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
                items=[UserResultMapper.from_model(user) for user in items],
                total=total,
                page=page,
                page_size=page_size,
            )

    def update_user(
        self,
        *,
        actor: UserResult,
        user_id: UUID,
        command: UpdateUserCommand,
        scope: UserManagementScope,
    ) -> UserResult:
        # CURRENT_USER 必须操作自己且不能改权限字段; ADMIN 必须是管理员且不能走管理端点改自己。
        if scope is UserManagementScope.CURRENT_USER:
            if actor.id != user_id:
                raise PermissionDeniedError
            if command.is_active_supplied or command.is_superuser_supplied:
                raise PermissionDeniedError
        else:
            if not actor.is_superuser:
                raise PermissionDeniedError
            if actor.id == user_id:
                raise SelfAdministrationError

        hashed_password = None
        # 密码哈希在打开 Session 前完成, 避免昂贵计算占用数据库连接或事务。
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
