import json
from pathlib import Path

import torch

INPUT_PT = Path("embedding/gemini_embeddings_filtered.pt")
CLUSTERED_JSONL = Path("embedding/cleaned_apartements_clustered.jsonl")
CENTROIDS_PATH = Path("embedding/cluster_centroids.pt")
OUTPUT_PT = Path("embedding/gemini_embeddings_clustered.pt")


def main() -> None:
    # Load cluster memberships from JSONL keyed by object_id
    memberships: dict[str, dict] = {}
    with CLUSTERED_JSONL.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            oid = str(record.get("object_id", "")).strip()
            cm = record.get("cluster_memberships")
            if oid and cm is not None:
                memberships[oid] = cm

    print(f"Loaded cluster memberships for {len(memberships)} listings")

    # Load the existing embedding store
    store = torch.load(INPUT_PT, map_location="cpu", weights_only=False)
    rows: list[dict] = store["rows"]

    # Inject cluster_memberships into each row
    missing = 0
    for row in rows:
        oid = str(row.get("object_id", "")).strip()
        cm = memberships.get(oid)
        if cm is None:
            row["cluster_memberships"] = {}
            missing += 1
        else:
            row["cluster_memberships"] = cm

    if missing:
        print(f"Warning: {missing} rows had no cluster membership")

    centroids_data = torch.load(CENTROIDS_PATH, map_location="cpu", weights_only=False)

    torch.save(
        {
            "embeddings": store["embeddings"],
            "rows": rows,
            "cluster_centroids": centroids_data["centroids"],
        },
        OUTPUT_PT,
    )
    print(
        f"Saved {len(rows)} rows with cluster memberships and {centroids_data['n_clusters']} centroids -> {OUTPUT_PT}"
    )


if __name__ == "__main__":
    main()
