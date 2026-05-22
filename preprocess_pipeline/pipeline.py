import json
import logging
import argparse

from pathlib import Path

from classifier import MODEL_ID, CLIPClassifier
from selector import ApartmentBinMap, QuotaSelector
from dedpup_scraped_listings import dedup_raw_listings
from dedup_images import dedup_images

# --- Configuration ---

MAX_IMAGES = 6
CONFIDENCE_THRESHOLD = 0.5

QUOTA = {
    "living_room": 2,
    "kitchen": 1,
    "bedroom": 2,
    "bathroom": 1,
}

FALLBACK = [
    ("hallway", 1),
    ("garden", 1),
    ("empty_room", MAX_IMAGES),
]


# --- Logging ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# --- Helpers ---


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def write_jsonl(records: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def find_images(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() == ".jpg")


# --- Pipeline ---


def run_pipeline(jsonl_path: Path, images_root: Path, output_path: Path) -> None:
    log.info(f"Loading listings from {jsonl_path}")
    records = load_jsonl(jsonl_path)
    log.info(f"  {len(records)} apartments found")

    classifier = CLIPClassifier()
    selector = QuotaSelector(quota=QUOTA, fallback=FALLBACK, max_images=MAX_IMAGES)

    output_records = []
    skipped = 0

    for i, record in enumerate(records):
        object_id = record.get("object_id")
        prefix = f"[{i+1}/{len(records)}]"

        if not object_id:
            log.warning(f"{prefix} Missing object_id — skipping")
            skipped += 1
            output_records.append(record)
            continue

        images = find_images(images_root / str(object_id))

        if not images:
            log.warning(f"{prefix} [{object_id}] No images found — skipping")
            skipped += 1
            output_records.append(
                {**record, "clip_selected_images": [], "clip_bin_map": {}}
            )
            continue

        log.info(f"{prefix} [{object_id}] Classifying {len(images)} images …")

        bin_map = ApartmentBinMap(object_id=str(object_id))
        for img_path in images:
            try:
                pred = classifier.classify(img_path)
                if pred.confidence >= CONFIDENCE_THRESHOLD:
                    bin_map.add(pred)
            except Exception as e:
                log.warning(f"  Could not classify {img_path.name}: {e}")

        result = selector.select(bin_map)
        log.info(
            f"{prefix} [{object_id}] Selected {result.total_selected}/{result.total_classified} images"
        )

        output_records.append(
            {
                **record,
                "clip_selected_images": result.selected_images,
                "clip_bin_map": result.bin_map,
                "clip_meta": {
                    "total_images": result.total_classified,
                    "total_selected": result.total_selected,
                    "model": MODEL_ID,
                },
            }
        )

    write_jsonl(output_records, output_path)
    log.info(f"Done. {len(output_records) - skipped} processed, {skipped} skipped.")


# --- Run ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Run preprocessing prerequisites before CLIP pipeline",
    )
    args = parser.parse_args()

    JSONL_PATH = Path("data/cleaned/cleaned_apartements.jsonl")
    IMAGES_DIR = Path("data/raw/images")
    OUTPUT_PATH = Path("preprocess_pipeline/cleaned_apartements_processed.jsonl")
    
    if args.prepare:
        dedup_raw_listings()
        dedup_images()
        
    run_pipeline(JSONL_PATH, IMAGES_DIR, OUTPUT_PATH)
