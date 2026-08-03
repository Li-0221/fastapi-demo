from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine

from app.core.config import get_database_settings
from app.db.session import DatabaseSessionManager


@lru_cache
def get_database_manager() -> DatabaseSessionManager:
    settings = get_database_settings()
    engine = create_engine(settings.url, pool_pre_ping=True)
    return DatabaseSessionManager(engine)


DatabaseManagerDep = Annotated[DatabaseSessionManager, Depends(get_database_manager)]
