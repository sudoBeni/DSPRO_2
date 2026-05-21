import torch

from .base import BaseRecommender
from .schemas import RatedItem, RecommendationResult


class KNearestRecommender(BaseRecommender):
    def recommend(
        self,
        rated_items: list[RatedItem],
        top_k: int = 10,
        include_liked: bool = False,
        min_per_like: int = 10,  # for >= 2 likes this value gets clamped
        excluded_ids: set[str] = frozenset(),
    ) -> list[RecommendationResult]:
        liked_ids = [item.object_id for item in rated_items if item.rating == 1]

        if not liked_ids:
            return []

        liked_indices = [
            self._id_to_idx[oid] for oid in liked_ids if oid in self._id_to_idx
        ]

        if not liked_indices:
            return []

        # handle min_per_like so reserved slots never exceed top_k
        effective_min_per_like = min(min_per_like, top_k // len(liked_indices))

        excluded_indices = self._build_excluded_indices(
            rated_items, include_liked, excluded_ids
        )

        best_score: dict[int, float] = {}
        per_like_candidates: list[list[tuple[int, float]]] = []

        for liked_idx in liked_indices:
            query = self._embeddings[liked_idx]
            sims = self._embeddings @ query

            for idx in excluded_indices:
                sims[idx] = -2.0

            k = min(top_k, sims.shape[0])
            top_scores, top_indices = torch.topk(sims, k=k)

            candidates = [
                (int(idx), score)
                for score, idx in zip(
                    top_scores.tolist(), top_indices.tolist(), strict=False
                )
            ]
            per_like_candidates.append(candidates)

            for idx, score in candidates:
                if score > best_score.get(idx, -2.0):
                    best_score[idx] = score

        if effective_min_per_like == 0:
            ranked = sorted(best_score.items(), key=lambda x: x[1], reverse=True)[
                :top_k
            ]
        else:
            # Reserve effective_min_per_like slots per liked item, then fill the rest globally
            reserved: dict[int, float] = {}
            for candidates in per_like_candidates:
                count = 0
                for idx, score in candidates:
                    if count >= effective_min_per_like:
                        break
                    if idx not in reserved:
                        reserved[idx] = score
                        count += 1

            remaining = top_k - len(reserved)
            filler = sorted(
                (
                    (idx, score)
                    for idx, score in best_score.items()
                    if idx not in reserved
                ),
                key=lambda x: x[1],
                reverse=True,
            )[: max(0, remaining)]

            ranked = sorted(
                list(reserved.items()) + filler, key=lambda x: x[1], reverse=True
            )[:top_k]

        return [
            RecommendationResult(
                object_id=self._object_ids[idx],
                similarity_score=round(score, 6),
            )
            for idx, score in ranked
        ]
