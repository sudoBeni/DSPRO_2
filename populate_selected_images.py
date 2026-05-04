"""
Populates data/selected_images/{object_id}/ from data/images/
using the clip_selected_images field in the JSONL listings file.
Run from the project root: uv run python populate_selected_images.py
"""

import json
import shutil
from pathlib import Path

JSONL_PATH = Path("data/cleaned_apartements_processed.jsonl")
IMAGES_DIR = Path("data/images")
OUTPUT_DIR = Path("data/selected_images")

copied = 0
missing = 0

with JSONL_PATH.open(encoding="utf-8") as f:
    for line in f:
        listing = json.loads(line)
        object_id = str(listing["object_id"])
        selected = listing.get("clip_selected_images") or []

        for entry in selected:
            filename = entry["filename"]
            src = IMAGES_DIR / filename
            if not src.exists():
                print(f"  missing: {src}")
                missing += 1
                continue

            dest_dir = OUTPUT_DIR / object_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / filename)
            copied += 1

print(f"\nDone: {copied} images copied, {missing} missing.")
