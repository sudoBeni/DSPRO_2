import json
import os
import time
from pathlib import Path
from typing import List

import torch
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-embedding-2-preview"
TASK_TYPE = "SEMANTIC_SIMILARITY"

JSONL_PATH = Path("apartements.jsonl")
IMAGES_DIR = Path("images")
OUTPUT_PATH = Path("multimodal_embeddings_gemini_2.pt")


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("set GEMINI_API_KEY in your environment variables.")

    client = genai.Client(api_key=api_key)
    embeddings: List[torch.Tensor] = []
    rows = []

    with JSONL_PATH.open("r", encoding="utf-8") as f:
        listings = [json.loads(line) for line in f if line.strip()]

    for i, item in enumerate(listings, start=1):
        object_id = str(item.get("object_id", "")).strip()
        image_dir = IMAGES_DIR / object_id
        image_paths = sorted(image_dir.glob("*.jpg"))

        postal_code = str(item.get("postal_code") or "Stadt unbekannt").strip()
        city = postal_code.split(" ", 1)[1] if " " in postal_code else postal_code
        short_description = str(
            item.get("short_description") or "keine kurz Beschreibung vorhanden"
        ).strip()
        n_rooms = str(item.get("n_rooms") or "Anzahl Zimmer unbekannt").strip()
        living_area_m2 = str(
            item.get("living_area_m2") or "Wohnfläche unbekannt"
        ).strip()
        rent_chf = str(item.get("rent_chf") or "Miete unbekannt").strip()
        description = " ".join(
            str(item.get("description") or "keine Beschreibung vorhanden").split()
        )[:300]

        text_prompt = (
            f"Immobilie in {city}: {short_description}. "
            f"die Immobilie hat {n_rooms} und {living_area_m2}. "
            f"Die monatliche Miete ist {rent_chf}. "
            f"Eigenschaften: {description}."
        )

        parts = [types.Part.from_text(text=text_prompt)]
        for image_path in image_paths:
            parts.append(
                types.Part.from_bytes(
                    data=image_path.read_bytes(), mime_type="image/jpeg"
                )
            )

        while True:
            try:
                response = client.models.embed_content(
                    model=MODEL,
                    contents=[types.Content(parts=parts)],
                    config=types.EmbedContentConfig(
                        task_type=TASK_TYPE, output_dimensionality=1536
                    ),
                )
                break
            except Exception as e:
                if "429" in str(e):
                    print("Rate limit hit. Sleeping for 60 seconds.")
                    time.sleep(60)
                    continue
                raise

        values = response.embeddings[0].values
        embedding = torch.tensor(values, dtype=torch.float32)
        embeddings.append(embedding)
        rows.append(
            {
                "object_id": object_id,
                "n_images": len(image_paths),
                "text_prompt": text_prompt,
            }
        )
        print(f"[{i}/{len(listings)}] embedded {object_id}")
        time.sleep(10)  # to avoid hitting rate limits

    if embeddings:
        embeddings_tensor = torch.stack(embeddings)
    else:
        embeddings_tensor = torch.empty((0, 0), dtype=torch.float32)

    torch.save({"embeddings": embeddings_tensor, "rows": rows}, OUTPUT_PATH)
    print(f"saved {len(rows)} embeddings -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
