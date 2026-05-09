from typing import Any

import torch
import torch.nn.functional as F

from .base import BaseRecommender
from .schemas import RatedItem, RecommendationResult


class FuzzyClusterRecommender(BaseRecommender):
    def __init__(
        self,
        embedding_store: dict[str, Any],
        centroid_weight: float = 1.0,
    ) -> None:
        super().__init__(embedding_store)
        self._centroid_weight = centroid_weight

        rows = embedding_store["rows"]

        n_clusters = 0
        for row in rows:
            cm = row.get("cluster_memberships") or {}
            if cm:
                n_clusters = len(cm)
                break
        self._n_clusters = n_clusters

        memberships = torch.zeros(len(rows), n_clusters, device=self._embeddings.device)
        for i, row in enumerate(rows):
            cm = row.get("cluster_memberships") or {}
            for c_str, val in cm.items():
                memberships[i, int(c_str)] = float(val)
        self._memberships = memberships  # [N, n_clusters]

        raw_centroids = embedding_store.get("cluster_centroids")
        if raw_centroids is not None:
            centroids = raw_centroids.float().to(self._embeddings.device)
            self._centroids = F.normalize(centroids, p=2, dim=1)  # [n_clusters, D]
        else:
            self._centroids = None

    def recommend(
        self,
        rated_items: list[RatedItem],
        top_k: int = 10,
        include_liked: bool = True,
    ) -> list[RecommendationResult]:
        dim = self._embeddings.shape[1]
        device = self._embeddings.device

        # Accumulate user signal per cluster: rating * membership * embedding
        user_signal = torch.zeros(
            self._n_clusters, dim, device=device
        )  # [n_clusters, D]
        total_likes = 0
        has_signal = False

        for item in rated_items:
            if item.rating == 0 or item.object_id not in self._id_to_idx:
                continue
            idx = self._id_to_idx[item.object_id]
            memberships_item = self._memberships[idx]  # [n_clusters]
            emb = self._embeddings[idx]  # [D]
            user_signal += (
                item.rating * memberships_item.unsqueeze(1) * emb.unsqueeze(0)
            )
            if item.rating > 0:
                total_likes += 1
            has_signal = True

        if not has_signal:
            return []

        # User affinity per cluster: normalise by number of likes so w sums reflect preference share
        if total_likes > 0:
            user_affinity = (
                self._memberships[
                    [
                        self._id_to_idx[i.object_id]
                        for i in rated_items
                        if i.rating > 0 and i.object_id in self._id_to_idx
                    ]
                ].sum(dim=0)
                / total_likes
            )  # [n_clusters]
        else:
            user_affinity = (
                torch.ones(self._n_clusters, device=device) / self._n_clusters
            )

        # Anchor each cluster vector at the centroid, then let user signal push/pull it
        if self._centroids is not None:
            # centroid_weight scales the centroid anchor relative to user signal magnitude
            cluster_vectors = (
                self._centroid_weight * self._centroids + user_signal
            )  # [n_clusters, D]
        else:
            cluster_vectors = user_signal

        # Score every candidate: weighted sum over clusters of
        #   user_affinity[c] * membership(item,c) * sim(item, cluster_vec[c])
        # sim computed as dot product after normalising cluster vectors
        norms = cluster_vectors.norm(dim=1, keepdim=True)
        nonzero = norms.squeeze(1) > 0
        cluster_vectors_norm = cluster_vectors.clone()
        cluster_vectors_norm[nonzero] = cluster_vectors[nonzero] / norms[nonzero]

        # [N, n_clusters]: cosine similarity of each item against each cluster vector
        cluster_sims = self._embeddings @ cluster_vectors_norm.T

        # Weight by user affinity and candidate membership
        weighted_sims = cluster_sims * self._memberships * user_affinity.unsqueeze(0)
        scores = weighted_sims.sum(dim=1)  # [N]

        excluded_indices = self._build_excluded_indices(rated_items, include_liked)
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
