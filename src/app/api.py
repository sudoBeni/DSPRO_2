import base64

from typing import List

from fastapi import APIRouter

from app.service import RecommendationService
from app.recommendation_schema import (
    SearchProfileRequest,
    ListingResponse,
    OnboardingImage,
)

router = APIRouter(prefix="/api", tags=["propertyfinder"])

recommendation_service = RecommendationService()


@router.get("/recommendations/onboarding", response_model=List[OnboardingImage])
def get_onboarding_recommendations() -> List[OnboardingImage]:
    onboarding_images = recommendation_service.get_onboarding_images()

    return map(
        lambda img: OnboardingImage(
            id=img.stem,
            label=img.stem,
            base64=f"data:image/jpeg;base64,{base64.b64encode(open(img, 'rb').read()).decode('utf-8')}",
        ),
        onboarding_images,
    )


@router.post("/recommendations/search", response_model=List[ListingResponse])
def search_recommendations(request: SearchProfileRequest) -> List[ListingResponse]:
    return recommendation_service.search(request)
