import random

from .base import BaseRecommender
from .schemas import RatedItem, RecommendationResult


class RandomBaselineRecommender(BaseRecommender):
    def recommend(
        self,
        rated_items: list[RatedItem],
        top_k: int = 10,
        include_liked: bool = False,
        excluded_ids: set[str] = frozenset(),
    ) -> list[RecommendationResult]:
        excluded_indices = self._build_excluded_indices(
            rated_items, include_liked=include_liked, excluded_ids=excluded_ids
        )

        candidates = [
            i for i in range(len(self._object_ids)) if i not in excluded_indices
        ]

        selected = random.sample(candidates, min(top_k, len(candidates)))

        return [
            RecommendationResult(object_id=self._object_ids[idx], similarity_score=0.0)
            for idx in selected
        ]
