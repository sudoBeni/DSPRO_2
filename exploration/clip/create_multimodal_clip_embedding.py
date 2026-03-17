import json
import os
import re

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

IMG_FOLDER = "./real_images"
JSON_FILE = "apartements.jsonl"
OUTPUT_PATH = "multimodal_embeddings.pt"
MODEL_NAME = "openai/clip-vit-base-patch32"


print("Starting CLIP embedding run...")
print(f"Images: {IMG_FOLDER}")
print(f"JSONL: {JSON_FILE}")
print(f"Output: {OUTPUT_PATH}")


def get_object_id(filename):
	match = re.match(r"^apartment_(\d+)_\d+\.(jpg)$", filename)
	if match:
		return match.group(1)
	return None


if torch.backends.mps.is_available():
	device = "mps"
elif torch.cuda.is_available():
	device = "cuda"
else:
	device = "cpu"
print(f"Using device: {device}")

print(f"Loading model: {MODEL_NAME}")
model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
processor = CLIPProcessor.from_pretrained(MODEL_NAME, use_fast=True)
model.eval()
print("Model loaded")

short_text_by_id = {}
with open(JSON_FILE, "r", encoding="utf-8") as file:
	for line in file:
		item = json.loads(line)
		short_description = item.get("short_description")
		object_id = item.get("object_id")
		if object_id is not None and short_description is not None:
			short_text_by_id[str(object_id)] = str(short_description).strip()

print(f"Loaded {len(short_text_by_id)} short descriptions")

jpg_files = [f for f in sorted(os.listdir(IMG_FOLDER)) if f.lower().endswith(".jpg")]
print(f"Found {len(jpg_files)} jpg files")

embeddings = []
rows = []

for idx, filename in enumerate(jpg_files, start=1):
	if idx % 100 == 0:
		print(f"Processed {idx}/{len(jpg_files)} images...")

	object_id = get_object_id(filename)
	if object_id is None:
		continue

	short_description = short_text_by_id.get(object_id)
	if not short_description:
		continue

	image_path = os.path.join(IMG_FOLDER, filename)
	image = Image.open(image_path).convert("RGB")

	inputs = processor(
		text=[short_description],
		images=image,
		return_tensors="pt",
		padding=True,
		truncation=True,
	)
	inputs = {key: value.to(device) for key, value in inputs.items()}

	with torch.no_grad():
		image_features = model.get_image_features(pixel_values=inputs["pixel_values"])
		text_features = model.get_text_features(
			input_ids=inputs["input_ids"],
			attention_mask=inputs["attention_mask"],
		)

		image_features = image_features / image_features.norm(dim=-1, keepdim=True)
		text_features = text_features / text_features.norm(dim=-1, keepdim=True)
		embedding = (image_features + text_features) / 2
		embedding = embedding / embedding.norm(dim=-1, keepdim=True)

	embeddings.append(embedding.cpu())
	rows.append(
		{
			"object_id": object_id,
			"filename": filename,
			"short_description": short_description,
		}
	)

if embeddings:
	embeddings = torch.cat(embeddings, dim=0)
else:
	embeddings = torch.empty((0, model.config.projection_dim), dtype=torch.float32)

torch.save({"embeddings": embeddings, "rows": rows}, OUTPUT_PATH)

print(f"Saved {len(rows)} embeddings to {OUTPUT_PATH}")
