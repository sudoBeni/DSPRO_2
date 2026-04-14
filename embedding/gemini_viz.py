from pathlib import Path

import torch
from citall import pca3d_explorer


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    embeddings_path = script_dir / "gemini_embeddings_filtered.pt"
    metadata_path = "preprocess_pipeline/cleaned_apartements_processed.jsonl"
    images_dir = "preprocess_pipeline/images"

    payload = torch.load(embeddings_path, map_location="cpu", weights_only=False)
    embeddings = payload["embeddings"]
    rows = payload["rows"]

    output, summary = pca3d_explorer(
        vectors_pt={"embeddings": embeddings, "rows": rows},
        metadata_path=metadata_path,
        metadata_key=["object_id"],
        rows_key=["object_id"],
        images_dir=images_dir,
        image_dir_key="object_id",
        max_images_per_embedding=6,
        hover_fields=["rent_chf", "postal_code"],
        click_fields=["object_id", "short_description", "rent_chf", "postal_code"],
        color_by="rent_chf",
        output_html=None,
        open_browser=True,
        return_summary=True,
    )
    print(summary)


if __name__ == "__main__":
    main()
