import base64

from typing import List

from fastapi import APIRouter

from app.service import RecommendationService
from app.recommendation_schema import (
    SearchProfileRequest,
    ListingResponse,
    OnboardingImageResponse,
)

router = APIRouter(prefix="/api", tags=["propertyfinder"])

recommendation_service = RecommendationService()


@router.get("/recommendations/onboarding", response_model=List[OnboardingImageResponse])
def get_onboarding_recommendations() -> List[OnboardingImageResponse]:
    onboarding_images = recommendation_service.get_onboarding_images()

    return map(
        lambda img: OnboardingImageResponse(
            id=img.stem,
            label=img.stem,
            base64=f"data:image/jpeg;base64,{base64.b64encode(open(img, 'rb').read()).decode('utf-8')}",
        ),
        onboarding_images,
    )


@router.post("/recommendations/search", response_model=List[ListingResponse])
def search_recommendations(request: SearchProfileRequest) -> List[ListingResponse]:
    """
    Placeholder recommendation endpoint.
    Next step: connect this route to recommendation_service.
    """
    return [
        ListingResponse(
            object_id="demo-listing-1",
            score=0.91,
            city=request.city or request.hard_filters.city,
            postal_code="6300",
            short_description="Helle 3.5-Zimmer-Wohnung mit Balkon",
            description="Demo response until the ranking pipeline is connected.",
            rent_chf=2950.0,
            n_rooms=3.5,
            living_area_m2=92.0,
            object_type=request.hard_filters.object_type or "wohnung",
            image_paths=[],
            source_url=None,
            matched_features=request.hard_filters.features,
        )
    ]
