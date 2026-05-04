from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import torch
from app.pipeline import Pipeline
from app.recommendation_schema import ListingResponse, SearchProfileRequest


class RecommendationService:
    def __init__(
        self,
        hard_data_path: str = "../data/cleaned_apartements_processed.jsonl",
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

        resolved_strategy = strategy or os.getenv("RECOMMENDER_STRATEGY", "gemini")
        self._pipeline = Pipeline(
            self._embedding_store, self._listings, strategy=resolved_strategy
        )

    def search(self, request: SearchProfileRequest) -> List[ListingResponse]:
        ranked = self._pipeline.run(
            request.liked_images, request.top_k, request.hard_facts
        )

        return [self._to_listing_response(item) for item in ranked]

    def get_onboarding_images(self) -> List[Path]:
        if not self._images_path.exists():
            return []

        all_images = [p for p in self._images_path.glob("**/*.jpg")]

        if not all_images:
            return []

        import random

        return random.sample(all_images, min(10, len(all_images)))

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
        path = path or Path("../embedding/gemini_embeddings_filtered.pt")
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
