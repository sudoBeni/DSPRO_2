import json
import torch
import skfuzzy as fuzz
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

EMBEDDINGS_PATH         = Path("embedding/gemini_embeddings_filtered.pt")
INPUT_JSONL             = Path("preprocess_pipeline/cleaned_apartements_processed.jsonl")
OUTPUT_JSONL            = Path("embedding/cleaned_apartements_clustered.jsonl")

TARGET_CLUSTER_SIZE_PCT = 20    # each cluster should contain this percentage of all objects
FUZZINESS               = 1.5  # 1 = hard, >2 = very fuzzy
PCA_COMPONENTS          = 10   # PCA down to this many dimensions (before clustering)

data = torch.load(EMBEDDINGS_PATH, weights_only=False)
embeddings = normalize(data["embeddings"].numpy(), norm="l2")
embeddings = PCA(n_components=PCA_COMPONENTS).fit_transform(embeddings)
embeddings = normalize(embeddings, norm="l2")
id_to_idx  = {str(r["object_id"]): i for i, r in enumerate(data["rows"])}

n_clusters = max(2, round(100 / TARGET_CLUSTER_SIZE_PCT))
print(f"Target cluster size: ~{TARGET_CLUSTER_SIZE_PCT}% → {n_clusters} clusters")

cntr, u, *_ = fuzz.cluster.cmeans(embeddings.T, c=n_clusters, m=FUZZINESS, error=0.005, maxiter=1000)


print(f"\nCluster membership summary (mean share per cluster):")
for c in range(n_clusters):
    print(f"  cluster {c}: avg membership {u[c].mean():.3f}, dominant in {(u.argmax(axis=0) == c).sum()} objects")


memberships = [
    {str(c): round(float(u[c, i]), 4) for c in range(n_clusters)}
    for i in range(len(embeddings))
]
idx_to_memberships = {i: memberships[i] for i in range(len(embeddings))}

with INPUT_JSONL.open() as fin, OUTPUT_JSONL.open("w") as fout:
    for line in fin:
        record = json.loads(line)
        oid = str(record.get("object_id", ""))
        idx = id_to_idx.get(oid)
        record["cluster_memberships"] = idx_to_memberships[idx] if idx is not None else None
        record["cluster_label"] = int(u[:, idx].argmax()) if idx is not None else None
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\nDone. Output: {OUTPUT_JSONL}")
