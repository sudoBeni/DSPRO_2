import json
import tempfile
from pathlib import Path

import torch
from citall import pca3d_explorer


def build_selected_images_dir(
    metadata_path: Path, base_dir: Path, tmp_dir: Path
) -> None:
    """Create per-object symlink dirs containing only the CLIP-selected images."""
    with metadata_path.open() as f:
        for line in f:
            record = json.loads(line)
            selected = record.get("clip_selected_images") or []
            if not selected:
                continue
            oid = str(record["object_id"])
            obj_dir = tmp_dir / oid
            obj_dir.mkdir(parents=True, exist_ok=True)
            for img in selected:
                src = (base_dir / img["path"]).resolve()
                dst = obj_dir / img["filename"]
                if src.exists() and not dst.exists():
                    dst.symlink_to(src)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    embeddings_path = script_dir / "gemini_embeddings_filtered.pt"
    metadata_path = script_dir / "cleaned_apartements_clustered.jsonl"
    base_dir = Path(".")

    payload = torch.load(embeddings_path, map_location="cpu", weights_only=False)
    embeddings = payload["embeddings"]
    rows = payload["rows"]

    with tempfile.TemporaryDirectory() as tmp:
        selected_images_dir = Path(tmp)
        build_selected_images_dir(metadata_path, base_dir, selected_images_dir)

        _, summary = pca3d_explorer(
            vectors_pt={"embeddings": embeddings, "rows": rows},
            metadata_path=metadata_path,
            metadata_key=["object_id"],
            rows_key=["object_id"],
            images_dir=selected_images_dir,
            image_dir_key="object_id",
            max_images_per_embedding=6,
            hover_fields=["rent_chf", "postal_code", "cluster_label"],
            click_fields=[
                "object_id",
                "short_description",
                "rent_chf",
                "postal_code",
                "cluster_memberships",
            ],
            color_by="cluster_label",
            output_html=None,
            open_browser=True,
            return_summary=True,
        )
        print(summary)


if __name__ == "__main__":
    main()
