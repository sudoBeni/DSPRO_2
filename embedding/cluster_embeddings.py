import json
from pathlib import Path

import numpy as np
import torch
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

EMBEDDINGS_PATH = Path("embedding/gemini_embeddings_filtered.pt")
INPUT_JSONL = Path("preprocess_pipeline/cleaned_apartements_processed.jsonl")
OUTPUT_JSONL = Path("embedding/cleaned_apartements_clustered.jsonl")
CENTROIDS_PATH = Path("embedding/cluster_centroids.pt")

N_CLUSTERS = 12
PCA_COMPONENTS = 8


data = torch.load(EMBEDDINGS_PATH, weights_only=False)
id_to_idx = {str(r["object_id"]): i for i, r in enumerate(data["rows"])}

# Preprocess: standardize -> PCA (GMM needs zero-mean, unit-variance input)
scaler = StandardScaler()
emb_scaled = scaler.fit_transform(data["embeddings"].numpy())
pca = PCA(n_components=PCA_COMPONENTS, random_state=42)
emb_pca = pca.fit_transform(emb_scaled)

print(
    f"Running GMM with {N_CLUSTERS} components on {PCA_COMPONENTS}-dim PCA embeddings"
)
gm = GaussianMixture(
    n_components=N_CLUSTERS,
    covariance_type="diag",
    max_iter=300,
    random_state=42,
    verbose=1,
)
gm.fit(emb_pca)
probs = gm.predict_proba(emb_pca)  # [N, N_CLUSTERS] — soft memberships

TEMPERATURE = 12  # higher = softer memberships; 1.0 = no change
logits = np.log(probs + 1e-10)
probs = np.exp(logits / TEMPERATURE)
probs = probs / probs.sum(axis=1, keepdims=True)

# Project GMM means (in PCA space) back to original embedding space for the recommender
pca_matrix = torch.tensor(
    pca.components_, dtype=torch.float32
)  # [PCA_COMPONENTS, D_orig]
scaler_mean = torch.tensor(scaler.mean_, dtype=torch.float32)  # [D_orig]
scaler_std = torch.tensor(scaler.scale_, dtype=torch.float32)  # [D_orig]
gmm_means_pca = torch.tensor(
    gm.means_, dtype=torch.float32
)  # [N_CLUSTERS, PCA_COMPONENTS]

# inverse PCA: x_scaled = means_pca @ pca.components_ + pca.mean_
pca_mean = torch.tensor(pca.mean_, dtype=torch.float32)  # [D_orig]
centroids_scaled = gmm_means_pca @ pca_matrix + pca_mean.unsqueeze(
    0
)  # [N_CLUSTERS, D_orig]
# inverse StandardScaler: x_orig = x_scaled * std + mean
centroids_orig = centroids_scaled * scaler_std.unsqueeze(0) + scaler_mean.unsqueeze(0)
centroids_norm = torch.nn.functional.normalize(
    torch.tensor(centroids_orig, dtype=torch.float32), p=2, dim=1
)

torch.save({"centroids": centroids_norm, "n_clusters": N_CLUSTERS}, CENTROIDS_PATH)
print(f"Saved {N_CLUSTERS} centroids -> {CENTROIDS_PATH}")

print("\nCluster membership summary:")
dominant = probs.argmax(axis=1)
for c in range(N_CLUSTERS):
    col = probs[:, c]
    print(
        f"  cluster {c:2d}: avg={col.mean():.3f}, std={col.std():.4f}, max={col.max():.4f}, dominant in {(dominant==c).sum()} objects"
    )

print(f"\nOverall membership std: {probs.std():.4f}")
print(f"Max membership: {probs.max():.4f}")

entropy = -np.sum(probs * np.log(probs + 1e-10), axis=1)
max_entropy = np.log(N_CLUSTERS)  # entropy if perfectly uniform
print(f"Avg entropy: {entropy.mean():.3f} / {max_entropy:.3f} (max if uniform)")
print(f"Avg entropy %: {100 * entropy.mean() / max_entropy:.1f}%")


memberships = [
    {str(c): round(float(probs[i, c]), 6) for c in range(N_CLUSTERS)}
    for i in range(len(emb_pca))
]
idx_to_memberships = {i: memberships[i] for i in range(len(emb_pca))}

with INPUT_JSONL.open() as fin, OUTPUT_JSONL.open("w") as fout:
    for line in fin:
        record = json.loads(line)
        oid = str(record.get("object_id", ""))
        idx = id_to_idx.get(oid)
        record["cluster_memberships"] = (
            idx_to_memberships[idx] if idx is not None else None
        )
        record["cluster_label"] = int(dominant[idx]) if idx is not None else None
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\nDone. Output: {OUTPUT_JSONL}")
