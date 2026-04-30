import re
from enum import Enum
from typing import Any

from app.recommendation_schema import OnboardingImage
from app.recommender import (
    FuzzyClusterRecommender,
    KNearestRecommender,
    RatedItem,
    WeightedVectorRecommender,
)


class RecommenderStrategy(str, Enum):
    K_NEAREST = "k_nearest"
    WEIGHTED_VECTOR = "weighted_vector"
    FUZZY_CLUSTER = "fuzzy_cluster"


class Pipeline:
    def __init__(
        self,
        embedding_store: dict[str, Any],
        strategy: str = "fuzzy_cluster",
    ) -> None:
        self._strategy = RecommenderStrategy(strategy)
        self._recommender = self._build_recommender(embedding_store)

    def _build_recommender(self, embedding_store: dict[str, Any]):
        if self._strategy == RecommenderStrategy.K_NEAREST:
            return KNearestRecommender(embedding_store)
        if self._strategy == RecommenderStrategy.WEIGHTED_VECTOR:
            return WeightedVectorRecommender(embedding_store)
        if self._strategy == RecommenderStrategy.FUZZY_CLUSTER:
            return FuzzyClusterRecommender(embedding_store)
        raise ValueError(f"Unknown strategy: {self._strategy}")

    def run(
        self, liked_images: list[OnboardingImage], top_k: int = 10
    ) -> list[dict[str, Any]]:
        rated_items = [
            RatedItem(object_id=self._parse_listing_id(img.id), rating=1)
            for img in liked_images
        ]
        results = self._recommender.recommend(rated_items, top_k=top_k)
        return [
            {"object_id": r.object_id, "score": r.similarity_score} for r in results
        ]

    def _parse_listing_id(self, image_path: str) -> str:
        match = re.search(r"apartment_(\d+)_\d+", image_path)
        if not match:
            raise ValueError(f"Invalid image path format: {image_path}")
        return match.group(1)
