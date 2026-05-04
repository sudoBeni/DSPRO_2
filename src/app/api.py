import base64
from typing import List

from app.recommendation_schema import (
    ListingResponse,
    OnboardingImage,
    SearchProfileRequest,
)
from app.service import RecommendationService
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["propertyfinder"])

recommendation_service = RecommendationService()


@router.get("/recommendations/onboarding", response_model=List[OnboardingImage])
def get_onboarding_recommendations() -> List[OnboardingImage]:
    onboarding_objects = recommendation_service.get_onboarding_objects()

    return [
        OnboardingImage(
            id=obj_id,
            label=obj_id,
            images=[
                f"data:image/jpeg;base64,{base64.b64encode(img_path.read_bytes()).decode()}"
                for img_path in img_paths
            ],
        )
        for obj_id, img_paths in onboarding_objects
    ]


@router.post("/recommendations/search", response_model=List[ListingResponse])
def search_recommendations(request: SearchProfileRequest) -> List[ListingResponse]:
    return recommendation_service.search(request)
