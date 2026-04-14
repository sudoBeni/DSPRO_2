from dataclasses import dataclass, field
from pathlib import Path

from classifier import ImagePrediction


@dataclass
class ApartmentBinMap:
    object_id: str
    bins: dict[str, list[ImagePrediction]] = field(default_factory=dict)

    def add(self, pred: ImagePrediction) -> None:
        self.bins.setdefault(pred.bin_label, []).append(pred)


@dataclass
class SelectionResult:
    object_id: str
    selected_images: list[dict]
    bin_map: dict[str, list[dict]]
    total_classified: int
    total_selected: int


def _to_dict(pred: ImagePrediction) -> dict:
    return {
        "filename": pred.image_path.name,
        "path": str(pred.image_path),
        "confidence": pred.confidence,
        "all_scores": pred.all_scores,
    }


class QuotaSelector:
    def __init__(
        self,
        quota: dict[str, int],
        fallback: list[tuple[str, int]],
        max_images: int = 6,
    ) -> None:
        self.quota = quota
        self.fallback = fallback
        self.max_images = max_images

    def _fill_from(
        self,
        bin_map: ApartmentBinMap,
        label: str,
        slots: int,
        selected: list[ImagePrediction],
        used: set[Path],
    ) -> None:
        available = sorted(
            (p for p in bin_map.bins.get(label, []) if p.image_path not in used),
            key=lambda p: p.confidence,
            reverse=True,
        )
        take = min(slots, len(available), self.max_images - len(selected))
        for pred in available[:take]:
            selected.append(pred)
            used.add(pred.image_path)

    def select(self, bin_map: ApartmentBinMap) -> SelectionResult:
        selected: list[ImagePrediction] = []
        used: set[Path] = set()

        for label, slots in self.quota.items():
            if len(selected) >= self.max_images:
                break
            self._fill_from(bin_map, label, slots, selected, used)

        for label, slots in self.fallback:
            if len(selected) >= self.max_images:
                break
            self._fill_from(bin_map, label, slots, selected, used)

        return SelectionResult(
            object_id=bin_map.object_id,
            selected_images=[_to_dict(p) for p in selected],
            bin_map={
                label: [
                    {**_to_dict(p), "selected": p.image_path in used} for p in entries
                ]
                for label, entries in bin_map.bins.items()
            },
            total_classified=sum(len(v) for v in bin_map.bins.values()),
            total_selected=len(selected),
        )
