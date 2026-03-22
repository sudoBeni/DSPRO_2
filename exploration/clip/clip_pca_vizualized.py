from pathlib import Path

import torch
from citall import pca3d_explorer


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    embeddings_path = script_dir / "multimodal_embeddings.pt"
    metadata_path = script_dir / "apartements.jsonl"
    images_dir = script_dir / "real_images"

    payload = torch.load(embeddings_path, map_location="cpu")
    embeddings = payload["embeddings"]
    rows = payload["rows"]

    output, summary = pca3d_explorer(
        vectors_pt={"embeddings": embeddings, "rows": rows},
        metadata_path=metadata_path,
        images_dir=images_dir,
        hover_fields=["rent_chf", "postal_code"],
        click_fields=["object_id", "short_description", "rent_chf", "postal_code"],
        color_by="rent_chf",
        open_browser=True,
        return_summary=True,
    )
    print(summary)


if __name__ == "__main__":
    main()
