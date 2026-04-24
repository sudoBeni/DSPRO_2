import json

locations = set()

with open("data/apartments.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        postal_code = item.get("postal_code")

        if postal_code:
            locations.add(str(postal_code).strip())

sorted_locations = sorted(locations)

with open("frontend/src/data/postal_codes.json", "w", encoding="utf-8") as f:
    json.dump(sorted_locations, f, ensure_ascii=False, indent=2)