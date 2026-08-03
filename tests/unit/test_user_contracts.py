from app.schemas.user import UserPutRequest, UserSelfPutRequest
from app.services.user_contracts import UpdateCurrentUserCommand, UpdateUserCommand


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
        password=None,
    )
    assert admin_command == UpdateUserCommand(
        email="managed@example.com",
        full_name="Managed User",
        password=None,
        is_active=False,
        is_superuser=True,
    )
