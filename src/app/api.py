import base64
import fcntl
import json
import logging
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List

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
    "weighted_vector",
    "k_nearest",
    "fuzzy_cluster",
    "random_baseline",
]


class _StrategyDeck:
    def __init__(self) -> None:
        self._deck: list[str] = []

    def next(self) -> str:
        """Return strategies in shuffled blocks so each appears equally often."""
        if not self._deck:
            self._deck = random.sample(STRATEGIES, len(STRATEGIES))
        return self._deck.pop()


_deck = _StrategyDeck()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/session")
def create_session() -> dict:
    strategy = _deck.next()
    logger.info("New session assigned — strategy=%s", strategy)
    return {"strategy": strategy}


@router.get("/recommendations/onboarding", response_model=List[OnboardingImage])
def get_onboarding_recommendations() -> List[OnboardingImage]:
    onboarding_objects = recommendation_service.get_onboarding_objects()

    return [
        OnboardingImage(
            id=obj_id,
            label=obj_id,
            images=[
                f"data:image/jpeg;base64,{base64.b64encode(img_path.read_bytes()).decode()}"
                for img_path in img_paths
            ],
        )
        for obj_id, img_paths in onboarding_objects
    ]


@router.post("/recommendations/search", response_model=List[ListingResponse])
def search_recommendations(request: SearchProfileRequest) -> List[ListingResponse]:
    logger.info("Search request — strategy=%s", request.strategy)
    return recommendation_service.search(request)


FEEDBACK_FILE = Path("../data/feedback.jsonl")
RECALL_LEVELS = [round(i * 0.1, 1) for i in range(11)]  # 0.0, 0.1, …, 1.0
RELEVANCE_THRESHOLD = 3  # rating 1-4, where 4=strongly agree


def _dcg(gains: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def _dcg_at_k(gains: list[float]) -> list[float]:
    cumulative = 0.0
    result = []
    for i, g in enumerate(gains):
        cumulative += g / math.log2(i + 2)
        result.append(round(cumulative, 4))
    return result


def _session_metrics(session: dict) -> dict | None:
    ratings = sorted(session.get("ratings", []), key=lambda x: x["position"])
    gains = [r["rating"] for r in ratings]  # graded relevance 1-3 (or 0)
    relevance = [1 if g >= RELEVANCE_THRESHOLD else 0 for g in gains]
    n = len(relevance)
    if n == 0:
        return None

    R = sum(relevance)
    p_at_k = sum(relevance) / n

    dcg = _dcg(gains)
    dcg_at_k = _dcg_at_k(gains)

    if R == 0:
        ap = 0.0
        pr_curve = [{"precision": 0.0, "recall": rl} for rl in RECALL_LEVELS]
    else:
        ap = (
            sum((sum(relevance[: k + 1]) / (k + 1)) * relevance[k] for k in range(n))
            / R
        )
        raw: list[dict] = [{"precision": 1.0, "recall": 0.0}]
        for k in range(n):
            hits = sum(relevance[: k + 1])
            raw.append({"precision": hits / (k + 1), "recall": hits / R})
        # 11-point interpolation: max precision at recall >= each level
        pr_curve = [
            {
                "precision": max(
                    (p["precision"] for p in raw if p["recall"] >= rl), default=0.0
                ),
                "recall": rl,
            }
            for rl in RECALL_LEVELS
        ]

    return {
        "strategy": session["strategy"],
        "p_at_k": p_at_k,
        "ap": ap,
        "dcg": dcg,
        "dcg_at_k": dcg_at_k,
        "pr_curve": pr_curve,
    }


@router.get("/analytics")
def get_analytics() -> dict:
    if not FEEDBACK_FILE.exists():
        return {
            "strategies": [],
            "overall": {"map": 0.0, "avg_p_at_k": 0.0, "n_sessions": 0},
        }

    sessions: list[dict] = []
    with FEEDBACK_FILE.open(encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if stripped:
                m = _session_metrics(json.loads(stripped))
                if m:
                    sessions.append(m)

    by_strategy: dict[str, list[dict]] = {s: [] for s in STRATEGIES}
    for s in sessions:
        if s["strategy"] in by_strategy:
            by_strategy[s["strategy"]].append(s)

    strategy_results = []
    for name in STRATEGIES:
        group = by_strategy[name]
        n = len(group)
        if n == 0:
            strategy_results.append(
                {
                    "name": name,
                    "n_sessions": 0,
                    "map": None,
                    "avg_p_at_k": None,
                    "pr_curve": [],
                }
            )
            continue

        avg_pr_curve = [
            {
                "recall": rl,
                "precision": round(
                    sum(s["pr_curve"][i]["precision"] for s in group) / n, 4
                ),
            }
            for i, rl in enumerate(RECALL_LEVELS)
        ]
        max_k = max(len(s["dcg_at_k"]) for s in group)
        avg_dcg_at_k = []
        for k in range(max_k):
            vals = [s["dcg_at_k"][k] for s in group if k < len(s["dcg_at_k"])]
            avg_dcg_at_k.append(round(sum(vals) / len(vals), 4))

        strategy_results.append(
            {
                "name": name,
                "n_sessions": n,
                "map": round(sum(s["ap"] for s in group) / n, 4),
                "avg_p_at_k": round(sum(s["p_at_k"] for s in group) / n, 4),
                "avg_dcg": round(sum(s["dcg"] for s in group) / n, 4),
                "avg_dcg_at_k": avg_dcg_at_k,
                "pr_curve": avg_pr_curve,
            }
        )

    total = len(sessions)
    return {
        "strategies": strategy_results,
        "overall": {
            "map": round(sum(s["ap"] for s in sessions) / total, 4) if total else 0.0,
            "avg_p_at_k": round(sum(s["p_at_k"] for s in sessions) / total, 4)
            if total
            else 0.0,
            "n_sessions": total,
        },
    }


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
