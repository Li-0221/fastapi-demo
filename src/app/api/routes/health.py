from typing import Literal

from fastapi import APIRouter

from app.schemas.common import ApiResponse, RsModel

router = APIRouter(tags=["health"])


class HealthData(RsModel):
    status: Literal["ok"]


@router.get("/health")
def health_check() -> ApiResponse[HealthData]:
    return ApiResponse(data=HealthData(status="ok"))
