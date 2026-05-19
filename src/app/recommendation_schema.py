from typing import List, Optional

from pydantic import BaseModel, Field


class OnboardingImage(BaseModel):
    id: str = Field(..., description="Object ID of the apartment.")
    label: str = Field(
        ..., description="A tag representing the user's preferred style."
    )
    images: List[str] = Field(..., description="Image URLs for this object.")


class HardFactsForm(BaseModel):
    location: str = Field(...)
    min_rooms: float | None = None
    max_rent_chf: int | None = None


class SearchProfileRequest(BaseModel):
    hard_facts: HardFactsForm = Field(...)
    liked_images: List[OnboardingImage] = Field(default_factory=list)
    disliked_images: List[OnboardingImage] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=100)
    strategy: str = Field(default="gemini")


class ListingResponse(BaseModel):
    object_id: str = Field(...)
    n_rooms: str = Field(...)
    living_area_m2: str = Field(...)
    rent_chf: str = Field(...)
    short_description: Optional[str] = Field(...)
    street: str = Field(...)
    postal_code: str = Field(...)
    source_url: str = Field(...)
    image_names: List[str] = Field(default_factory=list)
    match_score: float = Field(...)


class RatingItem(BaseModel):
    position: int
    object_id: str
    rating: int  # 1=strongly disagree, 2=somewhat disagree, 3=somewhat agree, 4=strongly agree


class FeedbackRequest(BaseModel):
    strategy: str
    hard_facts: HardFactsForm
    liked_object_ids: List[str]
    disliked_object_ids: List[str]
    skipped_object_ids: List[str]
    ratings: List[RatingItem]


__all__ = [
    "SearchProfileRequest",
    "ListingResponse",
    "OnboardingImage",
    "HardFactsForm",
    "RatingItem",
    "FeedbackRequest",
]
