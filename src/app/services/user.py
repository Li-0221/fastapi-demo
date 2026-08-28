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
    UserRecordCreate,
    UserRecordReplacement,
    UserRepository,
)
from app.schemas.common import PageData
from app.schemas.user import UserData


class UserService:
    def __init__(self, *, manager: DatabaseSessionManager) -> None:
        self.manager = manager

    def register_user(
        self,
        *,
        email: str,
        full_name: str | None,
        password: str,
    ) -> UserData:
        return self.create_user(
            email=email,
            full_name=full_name,
            password=password,
            is_active=True,
            is_superuser=False,
        )

    def create_user(
        self,
        *,
        email: str,
        full_name: str | None,
        password: str,
        is_active: bool,
        is_superuser: bool,
    ) -> UserData:
        record = UserRecordCreate(
            email=email.strip().casefold(),
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=is_active,
            is_superuser=is_superuser,
        )
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            try:
                user = repository.create(record)
                session.commit()
            except DuplicateUserRecordError:
                session.rollback()
                raise EmailAlreadyExistsError from None
            return UserData.model_validate(user, from_attributes=True)

    # 管理用例由 Service 再次校验 actor, 不能只依赖 Router 是否隐藏或暴露入口。
    def create_user_as_admin(
        self,
        *,
        actor: UserData,
        email: str,
        full_name: str | None,
        password: str,
        is_active: bool,
        is_superuser: bool,
    ) -> UserData:
        if not actor.is_superuser:
            raise PermissionDeniedError
        return self.create_user(
            email=email,
            full_name=full_name,
            password=password,
            is_active=is_active,
            is_superuser=is_superuser,
        )

    def get_user(self, *, actor: UserData, user_id: UUID) -> UserData:
        if not actor.is_superuser:
            raise PermissionDeniedError
        with self.manager.session_scope() as session:
            user = UserRepository(session).get_by_id(user_id)
            if user is None:
                raise UserNotFoundError
            return UserData.model_validate(user, from_attributes=True)

    def list_users(
        self,
        *,
        actor: UserData,
        page: int,
        page_size: int,
    ) -> PageData[UserData]:
        if not actor.is_superuser:
            raise PermissionDeniedError
        with self.manager.session_scope() as session:
            items, total = UserRepository(session).list_page(
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return PageData(
                items=[UserData.model_validate(user, from_attributes=True) for user in items],
                total=total,
                page=page,
                page_size=page_size,
            )

    def update_current_user(
        self,
        *,
        actor: UserData,
        email: str,
        full_name: str | None,
    ) -> UserData:
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(actor.id)
            if user is None:
                raise UserNotFoundError
            record = UserRecordReplacement(
                email=email.strip().casefold(),
                full_name=full_name,
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
            return UserData.model_validate(user, from_attributes=True)

    def change_current_user_password(
        self,
        *,
        actor: UserData,
        current_password: str,
        new_password: str,
    ) -> None:
        with self.manager.session_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id_for_update(actor.id)
            if user is None:
                raise UserNotFoundError
            if not verify_password(current_password, user.hashed_password):
                raise InvalidCurrentPasswordError
            repository.change_password(
                user=user,
                hashed_password=hash_password(new_password),
            )
            session.commit()

    def update_user_as_admin(
        self,
        *,
        actor: UserData,
        user_id: UUID,
        email: str,
        full_name: str | None,
        password: str | None,
        is_active: bool,
        is_superuser: bool,
    ) -> UserData:
        if not actor.is_superuser:
            raise PermissionDeniedError
        if actor.id == user_id:
            raise SelfAdministrationError

        hashed_password = hash_password(password) if password is not None else None
        record = UserRecordReplacement(
            email=email.strip().casefold(),
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=is_active,
            is_superuser=is_superuser,
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
            return UserData.model_validate(user, from_attributes=True)

    def delete_user(
        self,
        *,
        actor: UserData,
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
