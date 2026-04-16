from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import torch


from app.recommendation_schema import ListingResponse, SearchProfileRequest
from app.pipeline import Pipeline


class RecommendationService:
    def __init__(
        self,
        hard_data_path: str = "../data/apartments.jsonl",
        images_path: str = "../data/images",
    ) -> None:
        self._data_path = Path(hard_data_path)
        self._images_path = Path(images_path)
        self._embedding_store = self._load_embedding_store()
        self._listings = self._load_listings()

    def search(self, request: SearchProfileRequest) -> List[ListingResponse]:
        pipeline = Pipeline(self._embedding_store, self._listings)

        ranked = pipeline.run(request.liked_images, request.top_k)

        return [self._to_listing_response(item) for item in ranked]

    def get_onboarding_images(self) -> List[Path]:
        if not self._images_path.exists():
            return []

        all_images = [
            p
            for p in self._images_path.glob("*.jpg")
        ]

        if not all_images:
            return []

        import random

        return random.sample(all_images, min(10, len(all_images)))


    def _load_listings(self) -> List[Dict[str, Any]]:
        if not self._data_path.exists():
            raise FileNotFoundError(f"Data file not found at {self._data_path}")

        with self._data_path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]


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
        image_paths = self._get_image_paths(item)

        return ListingResponse(
            object_id=object_id,
            n_rooms=str(item.get("n_rooms", "")),
            living_area_m2=str(item.get("living_area_m2", "")),
            rent_chf=str(item.get("rent_chf", "")),
            short_description=item.get("short_description"),
            street=str(item.get("street", "")),
            postal_code=str(item.get("postal_code", "")),
            source_url=str(item.get("source_url", "")),
            image_paths=image_paths,
        )


    def _get_image_paths(self, item: Dict[str, Any]) -> List[str]:
        image_paths = item.get("image_paths")
        if isinstance(image_paths, list):
            return [str(path) for path in image_paths]
        return []


__all__ = ["RecommendationService"]
