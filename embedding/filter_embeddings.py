from pathlib import Path
from typing import Set

import torch

INPUT_PATH = Path(__file__).parent / "gemini_embeddings_checkpoint.pt"
OUTPUT_PATH = Path(__file__).parent / "gemini_embeddings_filtered.pt"

OUTLIER_IDS: Set[str] = {
    "4002957653",
    "4002980641",
    "4002980192",
    "4002790593",
    "4002790581",
    "4002790590",
    "4002790562",
    "4002956406",
    "4002968793",
    "4002968796",
    "4002968794",
    "4002968792",
    "4002734470",
    "4002908095",
    "4002971448",
    "4002971451",
    "4002971449",
    "4002971443",
    "4002971447",
    "4002971441",
    "4002916480",
    "4002697425",
}


def filter_embeddings(pt_path: Path, outlier_ids: Set[str], output_path: Path) -> None:
    payload = torch.load(pt_path, map_location="cpu", weights_only=False)
    embeddings = payload["embeddings"]
    rows = payload["rows"]

    keep = [i for i, r in enumerate(rows) if r["object_id"] not in outlier_ids]
    removed = len(rows) - len(keep)

    torch.save(
        {"embeddings": embeddings[keep], "rows": [rows[i] for i in keep]},
        output_path,
    )
    print(f"Removed {removed} outliers. Kept {len(keep)} embeddings -> {output_path}")


if __name__ == "__main__":
    filter_embeddings(INPUT_PATH, OUTLIER_IDS, OUTPUT_PATH)
