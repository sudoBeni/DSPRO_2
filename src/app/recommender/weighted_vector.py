import torch

from .base import BaseRecommender
from .schemas import RatedItem, RecommendationResult


class WeightedVectorRecommender(BaseRecommender):
    def recommend(
        self,
        rated_items: list[RatedItem],
        top_k: int = 10,
        include_liked: bool = True,
        excluded_ids: set[str] = frozenset(),
    ) -> list[RecommendationResult]:
        liked_indices = [
            self._id_to_idx[item.object_id]
            for item in rated_items
            if item.rating == 1 and item.object_id in self._id_to_idx
        ]
        disliked_indices = [
            self._id_to_idx[item.object_id]
            for item in rated_items
            if item.rating == -1 and item.object_id in self._id_to_idx
        ]

        if not liked_indices and not disliked_indices:
            return []

        # Build query vector: sum liked embeddings, subtract disliked embeddings
        query = torch.zeros(self._embeddings.shape[1], device=self._embeddings.device)
        for idx in liked_indices:
            query = query + self._embeddings[idx]
        for idx in disliked_indices:
            query = query - self._embeddings[idx]

        query_norm = query.norm()
        if query_norm == 0:
            return []
        query = query / query_norm

        sims = self._embeddings @ query

        excluded_indices = self._build_excluded_indices(
            rated_items, include_liked, excluded_ids
        )
        for idx in excluded_indices:
            sims[idx] = -2.0

        k = min(top_k, sims.shape[0])
        top_scores, top_indices = torch.topk(sims, k=k)

        return [
            RecommendationResult(
                object_id=self._object_ids[int(idx)],
                similarity_score=round(score, 6),
            )
            for score, idx in zip(
                top_scores.tolist(), top_indices.tolist(), strict=False
            )
        ]
