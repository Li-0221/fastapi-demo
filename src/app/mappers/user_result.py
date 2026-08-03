from app.models.user import User
from app.services.user_contracts import UserResult


class UserResultMapper:
    @staticmethod
    def from_model(user: User) -> UserResult:
        return UserResult(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
