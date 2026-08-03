from app.mappers.user import UserCommandMapper
from app.schemas.user import UserPatchRequest


def test_empty_patch_maps_every_field_as_unsupplied() -> None:
    command = UserCommandMapper.patch(UserPatchRequest.model_validate({}))

    assert command.email is None
    assert command.email_supplied is False
    assert command.full_name is None
    assert command.full_name_supplied is False
    assert command.password is None
    assert command.password_supplied is False
    assert command.is_active is None
    assert command.is_active_supplied is False
    assert command.is_superuser is None
    assert command.is_superuser_supplied is False
