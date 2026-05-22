import json
import logging
from pathlib import Path

original_file_path = Path("data/raw/apartements.jsonl")
cleaned_file_path = Path("data/cleaned/cleaned_apartements.jsonl")

# Logger set up
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def dedup_raw_listings() -> None:
    """
    This method goes through the raw Data and appends non-duplicates
    To a cleaned jsonl file for further processing
    """

    cleaned_file_path.parent.mkdir(parents=True, exist_ok=True)

    seen_ids = set()
    listings_count = 0

    with original_file_path.open("r", encoding="utf-8") as f:
        listings = [json.loads(line) for line in f if line.strip()]

    for item in listings:
        object_id = item.get("object_id")
        listings_count += 1

        if not object_id or object_id in seen_ids:
            continue

        seen_ids.add(object_id)

        apartment_listing = {
            "n_rooms": item.get("n_rooms"),
            "living_area_m2": item.get("living_area_m2"),
            "rent_chf": item.get("rent_chf"),
            "short_description": item.get("short_description"),
            "street": item.get("street"),
            "postal_code": item.get("postal_code"),
            "last_renovation_year": item.get("last_renovation_year"),
            "year_of_construction": item.get("year_of_construction"),
            "description": item.get("description"),
            "object_id": object_id,
            "source_url": item.get("source_url"),
            "scraped_at": item.get("scraped_at"),
        }

        with cleaned_file_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(apartment_listing, ensure_ascii=False) + "\n")

    log.info(f"Total listings checked: {listings_count}")
    log.info(f"Actual listings wrote in cleaned file: {len(seen_ids)}")


if __name__ == "__main__":
    dedup_raw_listings()
