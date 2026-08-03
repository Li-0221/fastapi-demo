from app.schemas.common import PageData
from app.schemas.user import UserData
from app.services.user_contracts import UserPageResult, UserResult


class UserPresenter:
    @staticmethod
    def detail(user: UserResult) -> UserData:
        return UserData(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @classmethod
    def page(cls, result: UserPageResult) -> PageData[UserData]:
        return PageData(
            items=[cls.detail(user) for user in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )
