from typing import Literal

from fastapi import APIRouter

from app.schemas.common import ApiResponse, ResponseModel

router = APIRouter(tags=["health"])


class HealthData(ResponseModel):
    status: Literal["ok"]


@router.get("/health")
def health_check() -> ApiResponse[HealthData]:
    return ApiResponse(data=HealthData(status="ok"))
