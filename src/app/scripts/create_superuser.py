from getpass import getpass

from app.dependencies.database import get_database_manager
from app.services.user import UserService
from app.services.user_contracts import CreateUserCommand


def main() -> None:
    email = input("Email: ").strip()
    password = getpass("Password: ")
    full_name = input("Full name (optional): ").strip() or None
    command = CreateUserCommand(
        email=email,
        full_name=full_name,
        password=password,
        is_active=True,
        is_superuser=True,
    )

    service = UserService(manager=get_database_manager())
    user = service.create_user(command)
    print(f"Created superuser: {user.id}")


if __name__ == "__main__":
    main()
