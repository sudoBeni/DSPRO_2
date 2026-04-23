from pathlib import Path
from typing import Set

import torch

INPUT_PATH = Path(__file__).parent / "gemini_embeddings.pt"
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
    "4002972441",
    "4002979193",
    "4002985521",
    "4002954009",
    "4002943999",
    "4002986838",
    "4002985530",
    "123456204",
    "4002990163",
    "123456053",
    "123456568",
    "4002983367",
    "4002985515",
    "4002982270",
    "123456091",
    "123456720",
    "4002972434",
    "4002985524",
    "4002983376",
    "4002907793",
    "123456952",
    "4002982265",
    "4002983366",
    "123456686",
    "123456579",
    "123456940",
    "4002980345",
    "4002977190",
    "4002948571",
    "4002982258",
    "4002982278",
    "4002947331",
    "4002985529",
    "4002982274",
    "4002947328",
    "4002977182",
    "123456550",
    "4002954010",
    "123456750",
    "123456513",
    "123456186",
    "123456287",
    "123456635",
    "123456577",
    "123456423",
    "123456875",
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
