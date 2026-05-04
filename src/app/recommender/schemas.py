from pydantic import BaseModel, Field


class RatedItem(BaseModel):
    object_id: str = Field(..., description="Listing object ID")
    rating: int = Field(..., description="1=liked, -1=disliked, 0=skipped")


class RecommendationResult(BaseModel):
    object_id: str
    similarity_score: float
