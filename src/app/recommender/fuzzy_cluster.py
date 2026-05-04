from typing import Any

import torch

from .base import BaseRecommender
from .schemas import RatedItem, RecommendationResult


class FuzzyClusterRecommender(BaseRecommender):
    def __init__(
        self,
        embedding_store: dict[str, Any],
        normalize_cluster_vectors: bool = False,
    ) -> None:
        super().__init__(embedding_store)
        self._normalize_cluster_vectors = normalize_cluster_vectors

        rows = embedding_store["rows"]

        n_clusters = 0
        for row in rows:
            cm = row.get("cluster_memberships") or {}
            if cm:
                n_clusters = len(cm)
                break
        self._n_clusters = n_clusters

        memberships = torch.zeros(len(rows), n_clusters)
        for i, row in enumerate(rows):
            cm = row.get("cluster_memberships") or {}
            for c_str, val in cm.items():
                memberships[i, int(c_str)] = float(val)
        self._memberships = memberships  # [N, n_clusters]

    def recommend(
        self,
        rated_items: list[RatedItem],
        top_k: int = 10,
        include_liked: bool = True,
        excluded_ids: set[str] = frozenset(),
    ) -> list[RecommendationResult]:
        dim = self._embeddings.shape[1]
        cluster_vectors = torch.zeros(self._n_clusters, dim)  # [n_clusters, D]
        has_signal = False

        for item in rated_items:
            if item.rating == 0 or item.object_id not in self._id_to_idx:
                continue
            idx = self._id_to_idx[item.object_id]
            memberships_item = self._memberships[idx]  # [n_clusters]
            emb = self._embeddings[idx]  # [D]
            # each cluster vector gets a share proportional to the item's membership
            cluster_vectors += (
                item.rating * memberships_item.unsqueeze(1) * emb.unsqueeze(0)
            )
            has_signal = True

        if not has_signal:
            return []

        if self._normalize_cluster_vectors:
            norms = cluster_vectors.norm(dim=1, keepdim=True)  # [n_clusters, 1]
            nonzero = norms.squeeze(1) > 0
            cluster_vectors[nonzero] = cluster_vectors[nonzero] / norms[nonzero]

        # similarity of every item against every cluster vector: [N, n_clusters]
        cluster_sims = self._embeddings @ cluster_vectors.T
        # weight each cluster's similarity by the candidate item's membership in that cluster
        scores = (cluster_sims * self._memberships).sum(dim=1)  # [N]

        excluded_indices = self._build_excluded_indices(
            rated_items, include_liked, excluded_ids
        )
        for idx in excluded_indices:
            scores[idx] = -float("inf")

        k = min(top_k, scores.shape[0])
        top_scores, top_indices = torch.topk(scores, k=k)

        return [
            RecommendationResult(
                object_id=self._object_ids[int(idx)],
                similarity_score=round(float(score), 6),
            )
            for score, idx in zip(
                top_scores.tolist(), top_indices.tolist(), strict=False
            )
        ]
