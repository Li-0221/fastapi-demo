from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DatabaseManagerDep
from app.services.user import UserService


def get_user_service(manager: DatabaseManagerDep) -> UserService:
    return UserService(manager=manager)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
