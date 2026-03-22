from pathlib import Path

import torch
from citall import generate_pca_html_from_multimodal


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    embeddings_path = script_dir / "multimodal_embeddings_gemini_2.pt"
    metadata_path = script_dir / "apartements.jsonl"
    images_dir = script_dir / "images"

    payload = torch.load(embeddings_path, map_location="cpu")
    embeddings = payload["embeddings"]
    rows = payload["rows"]

    output, summary = generate_pca_html_from_multimodal(
        embeddings=embeddings,
        rows=rows,
        metadata_path=metadata_path,
        images_dir=images_dir,
        image_dir_key="object_id",
        max_images_per_embedding=6,
        hover_fields=["rent_chf", "postal_code"],
        click_fields=["object_id", "short_description", "rent_chf", "postal_code"],
        color_by="rent_chf",
        open_browser=True,
        return_summary=True,
    )


if __name__ == "__main__":
    main()
