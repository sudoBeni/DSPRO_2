from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


from app.recommendation_schema import ListingResponse, SearchProfileRequest


class RecommendationService:
    def __init__(
        self,
        hard_data_path: str = "../data/apartements.jsonl",
        images_path: str = "../data/images",
    ) -> None:
        self.data_path = Path(hard_data_path)
        self.images_path = Path(images_path)

    def search(self, request: SearchProfileRequest) -> List[ListingResponse]:
        listings = self._load_listings()

        # Placeholder ranking logic.
        # Later this should call your embedding / similarity pipeline.
        ranked = listings[: request.top_k]

        return [self._to_listing_response(item) for item in ranked]

    def get_onboarding_images(self) -> List[Path]:
        if not self.images_path.exists():
            return []

        all_images = [
            p
            for p in self.images_path.glob("*.jpg")
        ]

        if not all_images:
            return []

        import random

        return random.sample(all_images, min(10, len(all_images)))

    def _load_listings(self) -> List[Dict[str, Any]]:
        if not self.data_path.exists():
            return []

        with self.data_path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

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
