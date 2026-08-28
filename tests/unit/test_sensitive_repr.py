import secrets

from app.repositories.user import UserRecordCreate
from app.schemas.auth import AccessTokenResponse
from app.schemas.user import UserPasswordChangeRequest, UserRegisterRequest
from app.services.auth import AccessTokenResult


def test_sensitive_values_do_not_appear_in_contract_reprs() -> None:
    sensitive_value = secrets.token_urlsafe(24)
    representations = (
        repr(
            UserRegisterRequest(
                email="repr-check@example.com",
                password=sensitive_value,
            )
        ),
        repr(
            UserPasswordChangeRequest.model_validate(
                {
                    "currentPassword": sensitive_value,
                    "newPassword": sensitive_value,
                }
            )
        ),
        repr(
            AccessTokenResponse(
                access_token=sensitive_value,
                expires_in=1800,
            )
        ),
        repr(
            UserRecordCreate(
                email="repr-check@example.com",
                full_name=None,
                hashed_password=sensitive_value,
                is_active=True,
                is_superuser=False,
            )
        ),
        repr(AccessTokenResult(access_token=sensitive_value, expires_in=1800)),
    )

    assert all(sensitive_value not in representation for representation in representations)
