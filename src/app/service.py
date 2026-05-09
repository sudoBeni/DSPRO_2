from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

import torch
from app.pipeline import Pipeline
from app.recommendation_schema import ListingResponse, SearchProfileRequest


class RecommendationService:
    def __init__(
        self,
        hard_data_path: str = "../data/cleaned_apartements_pt_aligned.jsonl",
        images_path: str = "../data/selected_images/",
        all_images_path: str = "../data/images/",
        strategy: str | None = None,
    ) -> None:
        self._data_path = Path(hard_data_path)
        self._images_path = Path(images_path)
        self._all_images_path = Path(all_images_path)
        self._embedding_store = self._load_embedding_store()
        self._listings = self._load_listings()
        self._listings_by_object_id = self._index_listings_by_object_id(self._listings)
        self._onboarding_eligible: set[str] = self._compute_onboarding_eligible()

        self._pipelines: dict[str, Pipeline] = {}

    def _compute_onboarding_eligible(
        self, isolation_percentile_cutoff: float = 7.5
    ) -> set[str]:
        """Exclude the most isolated objects from onboarding so farthest-point
        sampling doesn't always gravitate toward embedding-space outliers."""
        embeddings = self._embedding_store.get("embeddings")
        rows = self._embedding_store.get("rows", [])
        if embeddings is None or len(rows) == 0:
            return set()
        import torch.nn.functional as F

        emb = F.normalize(embeddings.float(), p=2, dim=1)
        avg_sims = (emb @ emb.T).mean(dim=1)  # [N]
        threshold = float(
            avg_sims.kthvalue(
                max(1, int(len(avg_sims) * isolation_percentile_cutoff / 100))
            ).values
        )
        eligible = {
            str(rows[i]["object_id"])
            for i in range(len(rows))
            if float(avg_sims[i]) >= threshold
        }
        excluded = len(rows) - len(eligible)
        print(
            f"Onboarding pool: {len(eligible)} eligible, {excluded} outliers excluded (bottom {isolation_percentile_cutoff}%)"
        )
        return eligible

    def _get_pipeline(self, strategy: str) -> Pipeline:
        if strategy not in self._pipelines:
            self._pipelines[strategy] = Pipeline(
                self._embedding_store, self._listings, strategy=strategy
            )
        return self._pipelines[strategy]

    def search(self, request: SearchProfileRequest) -> List[ListingResponse]:
        pipeline = self._get_pipeline(request.strategy)
        ranked = pipeline.run(request.liked_images, request.top_k, request.hard_facts)
        return [self._to_listing_response(item) for item in ranked]

    def get_onboarding_objects(self, n: int = 10) -> list[tuple[str, list[Path]]]:
        if not self._images_path.exists():
            return []

        MIN_IMAGES = 4
        obj_dirs = {
            d.name: d
            for d in self._images_path.iterdir()
            if d.is_dir()
            and sum(1 for _ in d.glob("*.jpg")) >= MIN_IMAGES
            and (not self._onboarding_eligible or d.name in self._onboarding_eligible)
        }
        if not obj_dirs:
            return []

        selected_ids = self._farthest_point_sample(list(obj_dirs.keys()), n)
        return [(oid, sorted(obj_dirs[oid].glob("*.jpg"))) for oid in selected_ids]

    def _farthest_point_sample(self, candidate_ids: list[str], n: int) -> list[str]:
        """Pick n diverse object_ids using farthest-point sampling on embeddings.

        Falls back to random sampling when an object_id has no embedding.
        """
        rows = self._embedding_store.get("rows", [])
        embeddings = self._embedding_store.get("embeddings")

        # Build index: object_id -> embedding row index
        id_to_idx: dict[str, int] = {
            str(row["object_id"]): i for i, row in enumerate(rows)
        }

        # Split candidates into those with and without an embedding
        with_emb = [oid for oid in candidate_ids if oid in id_to_idx]
        without_emb = [oid for oid in candidate_ids if oid not in id_to_idx]

        n = min(n, len(candidate_ids))

        if not with_emb or embeddings is None:
            return random.Random().sample(candidate_ids, n)

        # Extract the relevant embeddings
        indices = [id_to_idx[oid] for oid in with_emb]
        emb = embeddings[indices].float()
        norms = emb.norm(dim=1, keepdim=True).clamp(min=1e-8)
        emb = emb / norms  # shape: [M, D]

        # Farthest-point sampling
        selected_local: list[int] = [random.Random().randrange(len(with_emb))]
        selected_set: set[int] = set(selected_local)
        max_sim = torch.full((len(with_emb),), -float("inf"))

        while len(selected_local) < min(n, len(with_emb)):
            last = selected_local[-1]
            sims = emb @ emb[last]  # cosine similarities to last selected point
            max_sim = torch.maximum(max_sim, sims)

            # Mask already-selected so they are never picked again
            for idx in selected_set:
                max_sim[idx] = float("inf")

            next_idx = int(max_sim.argmin())
            selected_local.append(next_idx)
            selected_set.add(next_idx)

        result = [with_emb[i] for i in selected_local]

        # Fill remaining slots from unembedded candidates if needed
        remaining = n - len(result)
        if remaining > 0 and without_emb:
            result += random.Random().sample(
                without_emb, min(remaining, len(without_emb))
            )

        return result

    def _load_listings(self) -> List[Dict[str, Any]]:
        if not self._data_path.exists():
            raise FileNotFoundError(f"Data file not found at {self._data_path}")

        with self._data_path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _index_listings_by_object_id(
        self,
        listings: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        return {
            str(listing.get("object_id", "")): listing
            for listing in listings
            if listing.get("object_id") is not None
        }

    def _load_embedding_store(
        self,
        path: Path | None = None,
    ) -> dict[str, Any]:
        path = path or Path("../embedding/gemini_embeddings_clustered.pt")
        print(path)
        path = path.resolve()

        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        embedding_store = torch.load(path, map_location=device)

        return embedding_store

    def _to_listing_response(self, item: Dict[str, Any]) -> ListingResponse:
        object_id = str(item.get("object_id", ""))
        listing = self._listings_by_object_id.get(object_id)

        if listing is None:
            raise ValueError(f"No listing found for object_id '{object_id}'")

        image_names = self._get_image_names(object_id)

        return ListingResponse(
            object_id=object_id,
            n_rooms=str(listing.get("n_rooms", "")),
            living_area_m2=str(listing.get("living_area_m2", "")),
            rent_chf=str(listing.get("rent_chf", "")),
            short_description=listing.get("short_description"),
            street=str(listing.get("street", "")),
            postal_code=str(listing.get("postal_code", "")),
            source_url=str(listing.get("source_url", "")),
            image_names=image_names,
            match_score=float(item.get("score", 0.0)),
        )

    def _get_image_names(self, object_id: str) -> List[str]:
        matching_images = list(
            self._all_images_path.glob(f"apartment_{object_id}_*.jpg")
        )
        return sorted(path.name for path in matching_images)


__all__ = ["RecommendationService"]
