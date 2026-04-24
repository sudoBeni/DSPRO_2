from typing import List, Optional
from pathlib import Path

from pydantic import BaseModel, Field


class OnboardingImage(BaseModel):
    id: str = Field(..., description="Unique identifier for the onboarding image.")
    label: str = Field(
        ..., description="A tag representing the user's preferred style."
    )
    base64: str = Field(..., description="Base64-encoded image data.")


class SearchProfileRequest(BaseModel):
    liked_images: List[OnboardingImage] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=100)


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


__all__ = [
    "SearchProfileRequest",
    "ListingResponse",
    "OnboardingImage",
]
