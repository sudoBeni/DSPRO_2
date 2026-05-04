import json
from pathlib import Path

import torch

JSONL_PATH = Path("cleaned_apartements_processed.jsonl")
PT_PATH = Path("../embedding/gemini_embeddings_clustered.pt")
OUT_PATH = Path("cleaned_apartements_pt_aligned.jsonl")

store = torch.load(PT_PATH, map_location="cpu")
pt_ids = {str(row["object_id"]) for row in store["rows"]}

kept, removed = 0, 0
with JSONL_PATH.open() as f_in, OUT_PATH.open("w") as f_out:
    for line in f_in:
        if not line.strip():
            continue
        record = json.loads(line)
        if str(record["object_id"]) in pt_ids:
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            kept += 1
        else:
            removed += 1

print(f"Kept:    {kept}")
print(f"Removed: {removed}")
print(f"Output:  {OUT_PATH.resolve()}")
