from app.schemas.user import (
    UserCreateRequest,
    UserPatchRequest,
    UserRegisterRequest,
    UserSelfPatchRequest,
)
from app.services.user_contracts import (
    CreateUserCommand,
    RegisterUserCommand,
    UpdateUserCommand,
)


class UserCommandMapper:
    @staticmethod
    def register(request: UserRegisterRequest) -> RegisterUserCommand:
        return RegisterUserCommand(
            email=str(request.email),
            full_name=request.full_name,
            password=request.password,
        )

    @staticmethod
    def create(request: UserCreateRequest) -> CreateUserCommand:
        return CreateUserCommand(
            email=str(request.email),
            full_name=request.full_name,
            password=request.password,
            is_active=request.is_active,
            is_superuser=request.is_superuser,
        )

    @staticmethod
    def patch(request: UserPatchRequest) -> UpdateUserCommand:
        return UpdateUserCommand(
            email=str(request.email) if request.email is not None else None,
            email_supplied="email" in request.model_fields_set,
            full_name=request.full_name,
            full_name_supplied="full_name" in request.model_fields_set,
            password=request.password,
            password_supplied="password" in request.model_fields_set,
            is_active=request.is_active,
            is_active_supplied="is_active" in request.model_fields_set,
            is_superuser=request.is_superuser,
            is_superuser_supplied="is_superuser" in request.model_fields_set,
        )

    @staticmethod
    def self_patch(request: UserSelfPatchRequest) -> UpdateUserCommand:
        return UpdateUserCommand(
            email=str(request.email) if request.email is not None else None,
            email_supplied="email" in request.model_fields_set,
            full_name=request.full_name,
            full_name_supplied="full_name" in request.model_fields_set,
            password=request.password,
            password_supplied="password" in request.model_fields_set,
            is_active=None,
            is_active_supplied=False,
            is_superuser=None,
            is_superuser_supplied=False,
        )
