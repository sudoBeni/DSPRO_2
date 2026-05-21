import fcntl
import json
import logging
import random
from datetime import datetime, timezone
from typing import List

from app.analytics import FEEDBACK_FILE, STRATEGIES, get_analytics
from app.recommendation_schema import (
    FeedbackRequest,
    ListingResponse,
    OnboardingImage,
    SearchProfileRequest,
)
from app.service import RecommendationService
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["propertyfinder"])

recommendation_service = RecommendationService()

STRATEGIES = [
    "gemini",
    "single_vector",
    "k_nearest",
    "fuzzy_cluster",
    "random_baseline",
]


def _pick_least_used_strategy() -> str:
    counts: dict[str, int] = {s: 0 for s in STRATEGIES}
    if FEEDBACK_FILE.exists():
        with FEEDBACK_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    strategy = json.loads(line).get("strategy")
                    if strategy in counts:
                        counts[strategy] += 1
    min_count = min(counts.values())
    least_used = [s for s, c in counts.items() if c == min_count]
    return random.choice(least_used)


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/session")
def create_session() -> dict:
    strategy = _pick_least_used_strategy()
    logger.info("New session assigned — strategy=%s", strategy)
    return {"strategy": strategy}


@router.get("/recommendations/onboarding", response_model=List[OnboardingImage])
def get_onboarding_recommendations() -> List[OnboardingImage]:
    onboarding_objects = recommendation_service.get_onboarding_objects()

    return [
        OnboardingImage(
            id=obj_id,
            label=obj_id,
            images=[f"/api/images/{obj_id}/{img_path.name}" for img_path in img_paths],
        )
        for obj_id, img_paths in onboarding_objects
    ]


@router.get("/images/{object_id}/{filename}")
def get_onboarding_image(object_id: str, filename: str) -> FileResponse:
    img_path = recommendation_service.get_selected_images_path() / object_id / filename
    if not img_path.exists() or not img_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path=img_path, media_type="image/jpeg")


@router.post("/recommendations/search", response_model=List[ListingResponse])
def search_recommendations(request: SearchProfileRequest) -> List[ListingResponse]:
    logger.info("Search request — strategy=%s", request.strategy)
    return recommendation_service.search(request)


@router.get("/analytics")
def analytics_endpoint() -> dict:
    return get_analytics()


@router.get("/feedback/download")
def download_feedback() -> FileResponse:
    if not FEEDBACK_FILE.exists():
        raise HTTPException(status_code=404, detail="No feedback data yet.")
    return FileResponse(
        path=FEEDBACK_FILE,
        media_type="application/x-ndjson",
        filename="feedback.jsonl",
    )


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest) -> dict:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **request.model_dump(),
    }
    logger.info(
        "Feedback received — strategy=%s liked=%d disliked=%d skipped=%d ratings=%d",
        request.strategy,
        len(request.liked_object_ids),
        len(request.disliked_object_ids),
        len(request.skipped_object_ids),
        len(request.ratings),
    )
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"status": "ok"}
