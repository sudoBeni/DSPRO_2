from pathlib import Path
from typing import NamedTuple

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_ID = "openai/clip-vit-base-patch32"

BIN_PROMPTS = {
    "living_room": ["a photo of a living room"],
    "bedroom": ["a photo of a bedroom"],
    "kitchen": ["a photo of a kitchen"],
    "bathroom": ["a photo of a bathroom"],
    "exterior": [
        "a photo of the exterior of a building",
        "a photo of an apartment building from outside",
    ],
    "garden": ["a photo of a garden", "a photo of an outdoor terrace or balcony"],
    "hallway": ["a photo of a hallway or corridor", "a photo of an entrance or foyer"],
    "empty_room": ["a photo of an empty room with no furniture"],
    "not_relevant": [
        "a photo of a logo or brand name",
        "a blurry or uninformative photo",
        "a photo of a floor plan",
        "a photo of a blueprint or architectural drawing",
        "a photo of a document or text",
    ],
}


class ImagePrediction(NamedTuple):
    image_path: Path
    bin_label: str
    confidence: float
    all_scores: dict[str, float]


class CLIPClassifier:
    def __init__(self) -> None:
        if torch.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")
        print("Using device:", self.device)

        self.processor = CLIPProcessor.from_pretrained(MODEL_ID)
        self.model = CLIPModel.from_pretrained(MODEL_ID).to(self.device)
        self.model.eval()

        self._text_features = self._encode_prompts()

    def _encode_prompts(self) -> dict[str, torch.Tensor]:
        features = {}
        with torch.no_grad():
            for label, prompts in BIN_PROMPTS.items():
                inputs = self.processor(
                    text=prompts, return_tensors="pt", padding=True
                ).to(self.device)
                enc = self.model.get_text_features(**inputs)
                if not isinstance(enc, torch.Tensor):
                    enc = enc.pooler_output
                enc = enc / enc.norm(dim=-1, keepdim=True)
                mean = enc.mean(dim=0)
                features[label] = mean / mean.norm()
        return features

    def classify(self, image_path: Path) -> ImagePrediction:
        img = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=img, return_tensors="pt").to(self.device)

        with torch.no_grad():
            img_feat = self.model.get_image_features(**inputs)
            if not isinstance(img_feat, torch.Tensor):
                img_feat = img_feat.pooler_output
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)

            logit_scale = self.model.logit_scale.exp()
            raw_scores = {
                label: (logit_scale * img_feat @ feat.unsqueeze(-1)).squeeze().item()
                for label, feat in self._text_features.items()
            }

        probs = torch.softmax(torch.tensor(list(raw_scores.values())), dim=0).tolist()
        all_scores = {
            label: round(p, 4) for label, p in zip(raw_scores, probs, strict=False)
        }
        best_bin = max(all_scores, key=all_scores.__getitem__)

        return ImagePrediction(image_path, best_bin, all_scores[best_bin], all_scores)
