from app.exceptions import ErrorCode


def test_error_code_registry_uses_unique_nonzero_business_codes() -> None:
    business_codes = [code.business_code for code in ErrorCode]

    assert all(code > 0 for code in business_codes)
    assert len(business_codes) == len(set(business_codes))


def test_error_definition_owns_business_code_http_status_and_message() -> None:
    error = ErrorCode.EMAIL_ALREADY_EXISTS

    assert error.business_code == 10007
    assert error.http_status == 409
    assert error.default_message == "A user with this email already exists"
