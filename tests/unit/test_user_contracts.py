from app.schemas.user import UserPasswordChangeRequest, UserPutRequest, UserSelfPutRequest
from app.services.user_contracts import (
    ChangeCurrentUserPasswordCommand,
    UpdateCurrentUserCommand,
    UpdateUserCommand,
)


def test_put_requests_create_typed_replacement_commands() -> None:
    current_user_command = UpdateCurrentUserCommand.from_request(
        UserSelfPutRequest.model_validate(
            {
                "email": "current@example.com",
                "fullName": None,
            }
        )
    )
    admin_command = UpdateUserCommand.from_request(
        UserPutRequest.model_validate(
            {
                "email": "managed@example.com",
                "fullName": "Managed User",
                "isActive": False,
                "isSuperuser": True,
            }
        )
    )

    assert current_user_command == UpdateCurrentUserCommand(
        email="current@example.com",
        full_name=None,
    )
    assert admin_command == UpdateUserCommand(
        email="managed@example.com",
        full_name="Managed User",
        password=None,
        is_active=False,
        is_superuser=True,
    )


def test_password_change_request_creates_typed_command() -> None:
    command = ChangeCurrentUserPasswordCommand.from_request(
        UserPasswordChangeRequest.model_validate(
            {
                "currentPassword": "current-password",
                "newPassword": "replacement-password",
            }
        )
    )

    assert command == ChangeCurrentUserPasswordCommand(
        current_password="current-password",
        new_password="replacement-password",
    )
