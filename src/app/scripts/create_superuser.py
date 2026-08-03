from getpass import getpass

from app.dependencies.database import get_database_manager
from app.mappers.user import UserCommandMapper
from app.schemas.user import UserCreateRequest
from app.services.user import UserService


def main() -> None:
    email = input("Email: ").strip()
    password = getpass("Password: ")
    full_name = input("Full name (optional): ").strip() or None
    request = UserCreateRequest(
        email=email,
        full_name=full_name,
        password=password,
        is_active=True,
        is_superuser=True,
    )

    service = UserService(manager=get_database_manager())
    user = service.create_user(UserCommandMapper.create(request))
    print(f"Created superuser: {user.id}")


if __name__ == "__main__":
    main()
