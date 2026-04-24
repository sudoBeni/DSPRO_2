import os

from pathlib import Path
import torch
import base64
import re
import json

from typing import Any

from google import genai
from google.genai import types

from app.recommendation_schema import OnboardingImage

MODEL = "gemini-embedding-2-preview"
TASK_TYPE = "SEMANTIC_SIMILARITY"
IMAGES_DIR = Path("data/images")

class Pipeline:
    def __init__(self, embedding_store: dict[str, Any], listings: list[dict]) -> None:
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not self.GEMINI_API_KEY:
            raise RuntimeError("set GEMINI_API_KEY in your environment variables.")

        self._client = genai.Client(api_key=self.GEMINI_API_KEY)

        self._embedding_store = embedding_store

        self._listings = listings


    def run(self, liked_images: list[OnboardingImage], top_k: int = 10) -> list[dict[str, Any]]:
        scored_listings: list[dict[str, Any]] = []

        embeddings = self._embedding_store["embeddings"].float()
        rows = self._embedding_store["rows"]
        object_ids = [str(row["object_id"]) for row in rows]
        listing_by_object_id = {
            str(listing["object_id"]): listing for listing in self._listings
        }

        for image in liked_images:
            listing_id = self._parse_listing_id(image.id)
            listing = listing_by_object_id.get(listing_id)
            if not listing:
                raise ValueError(f"Listing with object_id {listing_id} not found.")

            text_prompt = self._create_text_prompt(listing)

            # TODO: get all images for the listing and create multimodal embedding
            liked_embedding = self._create_embedding([image.base64], text_prompt)

            if embeddings.shape[1] != liked_embedding.shape[0]:
                raise ValueError(
                    f"Embedding dimension mismatch: store has {embeddings.shape[1]}, "
                    f"query has {liked_embedding.shape[0]}."
                )

            query_idx = object_ids.index(listing_id)
            query_tensor = liked_embedding.to(embeddings.device)
            sims = embeddings @ query_tensor
            sims[query_idx] = -1  # remove the query itself

            k = min(top_k, sims.shape[0])
            top_scores, top_indices = torch.topk(sims, k=k)

            for score, idx in zip(top_scores.tolist(), top_indices.tolist()):
                matched_row = rows[idx]
                matched_object_id = str(matched_row["object_id"])

                scored_listings.append(
                    {
                        "score": float(score),
                        "object_id": matched_object_id,
                    }
                )

        ranked_listings = sorted(
            scored_listings,
            key=lambda item: item["score"],
            reverse=True,
        )

        return ranked_listings

    def _create_text_prompt(self, listing):
        postal_code = str(listing.get("postal_code") or "Stadt unbekannt").strip()
        city = postal_code.split(" ", 1)[1] if " " in postal_code else postal_code
        short_description = str(
                listing.get("short_description") or "keine kurz Beschreibung vorhanden"
            ).strip()
        n_rooms = str(listing.get("n_rooms") or "Anzahl Zimmer unbekannt").strip()
        living_area_m2 = str(
                listing.get("living_area_m2") or "Wohnfläche unbekannt"
            ).strip()
        rent_chf = str(listing.get("rent_chf") or "Miete unbekannt").strip()
        description = " ".join(
                str(listing.get("description") or "keine Beschreibung vorhanden").split()
            )[:300]

        text_prompt = (
                f"Immobilie in {city}: {short_description}. "
                f"die Immobilie hat {n_rooms} und {living_area_m2}. "
                f"Die monatliche Miete ist {rent_chf}. "
                f"Eigenschaften: {description}."
            )

        return text_prompt


    def _parse_listing_id(self, image_path: str) -> str:
        pattern = r"apartment_(\d+)_\d+"
        match = re.search(pattern, image_path)
        if not match:
            raise ValueError(f"Invalid image path format: {image_path}")
        return match.group(1)


    def _create_embedding(self, images, text_prompt: str):
        image_bytes = [self._decode_base64_image(image) for image in images]

        parts = [types.Part.from_text(text=text_prompt)]
        for image_byte in image_bytes:
            parts.append(
                types.Part.from_bytes(
                    data=image_byte, mime_type="image/jpeg"
                )
            )

        response = self._client.models.embed_content(
            model=MODEL,
            contents=[types.Content(parts=parts)],
            config=types.EmbedContentConfig(
                task_type=TASK_TYPE, output_dimensionality=3072
            ),
        )

        values = response.embeddings[0].values
        embedding = torch.tensor(values, dtype=torch.float32)

        return embedding

    def _decode_base64_image(self, image_str: str) -> bytes:
        if "," in image_str and image_str.startswith("data:"):
            image_str = image_str.split(",", 1)[1]
        return base64.b64decode(image_str)
