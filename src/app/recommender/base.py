from abc import ABC, abstractmethod
from typing import Any

import torch.nn.functional as F

from .schemas import RatedItem, RecommendationResult


class BaseRecommender(ABC):
    def __init__(self, embedding_store: dict[str, Any]) -> None:
        embeddings_raw = embedding_store["embeddings"].float()
        self._embeddings = F.normalize(embeddings_raw, p=2, dim=1)
        rows = embedding_store["rows"]
        self._object_ids = [str(row["object_id"]) for row in rows]
        self._id_to_idx = {oid: i for i, oid in enumerate(self._object_ids)}

    @abstractmethod
    def recommend(
        self,
        rated_items: list[RatedItem],
        top_k: int = 10,
        excluded_ids: set[str] = frozenset(),
    ) -> list[RecommendationResult]: ...

    def _build_excluded_indices(
        self,
        rated_items: list[RatedItem],
        include_liked: bool,
        excluded_ids: set[str] = frozenset(),
    ) -> set[int]:
        from_ratings = {
            self._id_to_idx[item.object_id]
            for item in rated_items
            if item.object_id in self._id_to_idx
            and (item.rating != 1 or not include_liked)
        }
        from_hard_facts = {
            self._id_to_idx[oid] for oid in excluded_ids if oid in self._id_to_idx
        }
        return from_ratings | from_hard_facts
