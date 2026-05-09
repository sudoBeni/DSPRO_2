import base64
import os
import re
from typing import Any

import torch
from app.recommendation_schema import HardFactsForm, OnboardingImage
from app.recommender import (
    FuzzyClusterRecommender,
    KNearestRecommender,
    RandomBaselineRecommender,
    SingleVectorRecommender,
)
from app.recommender.schemas import RatedItem
from google import genai
from google.genai import types

MODEL = "gemini-embedding-2-preview"
TASK_TYPE = "SEMANTIC_SIMILARITY"

_STRATEGY_CLASSES: dict[str, type | None] = {
    "gemini": None,  # no class because it creates a live gemini embedding
    "single_vector": SingleVectorRecommender,
    "k_nearest": KNearestRecommender,
    "fuzzy_cluster": FuzzyClusterRecommender,
    "random_baseline": RandomBaselineRecommender,
}


class Pipeline:
    def __init__(
        self,
        embedding_store: dict[str, Any],
        listings: list[dict],
        strategy: str = "gemini",
    ) -> None:
        if strategy not in _STRATEGY_CLASSES:
            raise ValueError(
                f"Unknown strategy {strategy!r}. "
                f"Choose from: {', '.join(_STRATEGY_CLASSES)}"
            )

        self._strategy = strategy
        self._listings = listings
        self._listing_by_object_id = {
            str(listing["object_id"]): listing for listing in listings
        }

        if strategy == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("Set GEMINI_API_KEY in your environment variables.")
            self._client = genai.Client(api_key=api_key)
            self._embeddings = torch.nn.functional.normalize(
                embedding_store["embeddings"].float(), p=2, dim=1
            )
            self._rows = embedding_store["rows"]
            self._object_ids = [str(row["object_id"]) for row in self._rows]
        else:
            self._recommender = _STRATEGY_CLASSES[strategy](embedding_store)

    def run(
        self,
        liked_images: list[OnboardingImage],
        top_k: int = 10,
        hard_facts: HardFactsForm | None = None,
        disliked_images: list[OnboardingImage] | None = None,
    ) -> list[dict[str, Any]]:
        if self._strategy == "gemini":
            return self._run_gemini(liked_images, top_k, hard_facts)
        return self._run_recommender(
            liked_images, top_k, hard_facts, disliked_images or []
        )

    # --- Gemini path ---

    def _run_gemini(
        self,
        liked_images: list[OnboardingImage],
        top_k: int,
        hard_facts: HardFactsForm | None,
    ) -> list[dict[str, Any]]:
        # Keep only the best score per object_id across all liked images
        best_scores: dict[str, float] = {}

        for image in liked_images:
            listing_id = self._parse_listing_id(image.id)
            listing = self._listing_by_object_id.get(listing_id)
            if not listing:
                raise ValueError(f"Listing with object_id {listing_id} not found.")

            text_prompt = self._create_text_prompt(listing)
            query_embedding = self._create_embedding(image.images, text_prompt)

            if self._embeddings.shape[1] != query_embedding.shape[0]:
                raise ValueError(
                    f"Embedding dimension mismatch: store has {self._embeddings.shape[1]}, "
                    f"query has {query_embedding.shape[0]}."
                )

            query_tensor = query_embedding.to(self._embeddings.device)
            query_tensor = torch.nn.functional.normalize(
                query_tensor.unsqueeze(0), p=2, dim=1
            ).squeeze(0)
            sims = self._embeddings @ query_tensor
            sims[self._object_ids.index(listing_id)] = -1.0

            # Fetch candidates until we have at least top_k passing hard filters for this image
            per_image_found: set[str] = set()
            k = min(top_k, sims.shape[0])
            while len(per_image_found) < top_k and k <= sims.shape[0]:
                top_scores, top_indices = torch.topk(sims, k=k)

                for score, idx in zip(
                    top_scores.tolist(), top_indices.tolist(), strict=False
                ):
                    matched_id = str(self._rows[idx]["object_id"])
                    matched_listing = self._listing_by_object_id.get(matched_id)
                    if not matched_listing:
                        continue
                    if hard_facts and not self._passes_hard_facts(
                        matched_listing, hard_facts
                    ):
                        continue
                    per_image_found.add(matched_id)
                    score_val = float(score)
                    if (
                        matched_id not in best_scores
                        or score_val > best_scores[matched_id]
                    ):
                        best_scores[matched_id] = score_val

                if len(per_image_found) < top_k:
                    new_k = min(k + top_k, sims.shape[0])
                    if new_k == k:
                        break
                    k = new_k

        scored = [{"object_id": oid, "score": s} for oid, s in best_scores.items()]
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]

    # --- Pre-computed embedding path ---

    def _run_recommender(
        self,
        liked_images: list[OnboardingImage],
        top_k: int,
        hard_facts: HardFactsForm | None,
        disliked_images: list[OnboardingImage] | None = None,
    ) -> list[dict[str, Any]]:
        rated_items = [
            RatedItem(object_id=self._parse_listing_id(img.id), rating=1)
            for img in liked_images
        ] + [
            RatedItem(object_id=self._parse_listing_id(img.id), rating=-1)
            for img in (disliked_images or [])
        ]
        excluded_ids = self._compute_excluded_ids(hard_facts) if hard_facts else set()

        results = self._recommender.recommend(
            rated_items, top_k=top_k, include_liked=False, excluded_ids=excluded_ids
        )
        return [
            {"object_id": r.object_id, "score": r.similarity_score} for r in results
        ]

    # --- Hard-facts helpers ---

    def _compute_excluded_ids(self, hard_facts: HardFactsForm) -> set[str]:
        return {
            str(listing["object_id"])
            for listing in self._listings
            if not self._passes_hard_facts(listing, hard_facts)
        }

    def _passes_hard_facts(self, listing: dict, hard_facts: HardFactsForm) -> bool:
        try:
            if hard_facts.min_rooms is not None:
                n_rooms = float(str(listing.get("n_rooms", "0")).split()[0])
                if n_rooms < hard_facts.min_rooms:
                    return False
            if hard_facts.max_rent_chf is not None:
                rent = int(re.sub(r"\D", "", str(listing.get("rent_chf", "0"))))
                if rent > hard_facts.max_rent_chf:
                    return False
        except Exception:
            return False
        return True

    # --- Gemini utilities ---

    def _parse_listing_id(self, image_id: str) -> str:
        if re.fullmatch(r"\d+", image_id):
            return image_id
        match = re.search(r"apartment_(\d+)_\d+", image_id)
        if not match:
            raise ValueError(f"Invalid image id format: {image_id}")
        return match.group(1)

    def _create_text_prompt(self, listing: dict) -> str:
        postal_code = str(listing.get("postal_code") or "Stadt unbekannt").strip()
        city = postal_code.split(" ", 1)[1] if " " in postal_code else postal_code
        short_description = str(
            listing.get("short_description") or "keine Kurzbeschreibung vorhanden"
        ).strip()
        n_rooms = str(listing.get("n_rooms") or "Anzahl Zimmer unbekannt").strip()
        living_area_m2 = str(
            listing.get("living_area_m2") or "Wohnfläche unbekannt"
        ).strip()
        rent_chf = str(listing.get("rent_chf") or "Miete unbekannt").strip()
        description = " ".join(
            str(listing.get("description") or "keine Beschreibung vorhanden").split()
        )[:300]

        return (
            f"Immobilie in {city}: {short_description}. "
            f"die Immobilie hat {n_rooms} und {living_area_m2}. "
            f"Die monatliche Miete ist {rent_chf}. "
            f"Eigenschaften: {description}."
        )

    def _create_embedding(self, images: list[str], text_prompt: str) -> torch.Tensor:
        parts = [types.Part.from_text(text=text_prompt)]
        for img in images:
            parts.append(
                types.Part.from_bytes(
                    data=self._decode_base64_image(img), mime_type="image/jpeg"
                )
            )
        response = self._client.models.embed_content(
            model=MODEL,
            contents=[types.Content(parts=parts)],
            config=types.EmbedContentConfig(
                task_type=TASK_TYPE, output_dimensionality=3072
            ),
        )
        return torch.tensor(response.embeddings[0].values, dtype=torch.float32)

    def _decode_base64_image(self, image_str: str) -> bytes:
        if "," in image_str and image_str.startswith("data:"):
            image_str = image_str.split(",", 1)[1]
        return base64.b64decode(image_str)
