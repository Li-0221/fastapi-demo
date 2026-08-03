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
        # PATCH 必须同时传递字段值和 supplied 标志, 才能区分“未提供”和“显式 null”。
        supplied_fields = request.model_fields_set
        return UpdateUserCommand(
            email=(
                str(request.email)
                if "email" in supplied_fields and request.email is not None
                else None
            ),
            email_supplied="email" in supplied_fields,
            full_name=request.full_name,
            full_name_supplied="full_name" in supplied_fields,
            password=request.password if "password" in supplied_fields else None,
            password_supplied="password" in supplied_fields,
            is_active=request.is_active if "is_active" in supplied_fields else None,
            is_active_supplied="is_active" in supplied_fields,
            is_superuser=request.is_superuser if "is_superuser" in supplied_fields else None,
            is_superuser_supplied="is_superuser" in supplied_fields,
        )

    @staticmethod
    def self_patch(request: UserSelfPatchRequest) -> UpdateUserCommand:
        # 自助更新不拥有权限字段, 即使未来 Router 误传也不会生成对应的 supplied 标志。
        supplied_fields = request.model_fields_set
        return UpdateUserCommand(
            email=(
                str(request.email)
                if "email" in supplied_fields and request.email is not None
                else None
            ),
            email_supplied="email" in supplied_fields,
            full_name=request.full_name,
            full_name_supplied="full_name" in supplied_fields,
            password=request.password if "password" in supplied_fields else None,
            password_supplied="password" in supplied_fields,
            is_active=None,
            is_active_supplied=False,
            is_superuser=None,
            is_superuser_supplied=False,
        )
