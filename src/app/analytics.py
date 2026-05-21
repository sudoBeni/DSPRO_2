import json
import math
import statistics as _stats
from pathlib import Path

FEEDBACK_FILE = Path(__file__).parent.parent.parent / "data" / "feedback.jsonl"
RELEVANCE_THRESHOLD = 3  # rating 1-4, where 4=strongly agree

STRATEGIES = [
    "gemini",
    "single_vector",
    "k_nearest",
    "fuzzy_cluster",
    "random_baseline",
]


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
    gains = [r["rating"] for r in ratings]
    relevance = [1 if g >= RELEVANCE_THRESHOLD else 0 for g in gains]
    # 2^r − 1 gain: strongly agree (4) → 3, agree (3) → 1, below threshold → 0
    # exponential weighting because a strongly agree is qualitatively more valuable than agree
    dcg_gains = [
        2 ** (g - RELEVANCE_THRESHOLD + 1) - 1 if g >= RELEVANCE_THRESHOLD else 0
        for g in gains
    ]
    n = len(relevance)
    if n == 0:
        return None

    R = sum(relevance)
    p_at_k = sum(relevance) / n

    dcg = _dcg(dcg_gains)
    dcg_at_k = _dcg_at_k(dcg_gains)

    precision_at_k = [sum(relevance[: k + 1]) / (k + 1) for k in range(n)]

    if R == 0:
        ap = 0.0
        pr_curve = [{"precision": 0.0, "recall": 0.0} for _ in range(n)]
    else:
        ap = (
            sum((sum(relevance[: k + 1]) / (k + 1)) * relevance[k] for k in range(n))
            / R
        )
        # raw PR curve: one point per rank position, no interpolation
        pr_curve = [
            {"precision": precision_at_k[k], "recall": sum(relevance[: k + 1]) / R}
            for k in range(n)
        ]

    mean_rating = sum(gains) / n

    return {
        "strategy": session["strategy"],
        "p_at_k": p_at_k,
        "ap": ap,
        "dcg": dcg,
        "dcg_at_k": dcg_at_k,
        "pr_curve": pr_curve,
        "precision_at_k": precision_at_k,
        "mean_rating": mean_rating,
        "ratings": gains,
    }


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
                    "avg_dcg": None,
                    "avg_dcg_at_k": [],
                    "avg_precision_at_k": [],
                    "pr_curve": [],
                    "auc_pr": None,
                    "rating_stats": None,
                }
            )
            continue

        # average raw PR curve by rank position across sessions
        max_pr_k = max(len(s["pr_curve"]) for s in group)
        avg_pr_curve = []
        for k in range(max_pr_k):
            pts = [s["pr_curve"][k] for s in group if k < len(s["pr_curve"])]
            avg_pr_curve.append(
                {
                    "precision": round(sum(p["precision"] for p in pts) / len(pts), 4),
                    "recall": round(sum(p["recall"] for p in pts) / len(pts), 4),
                }
            )
        # AUC-PR via trapezoidal rule over the averaged raw curve
        auc_pr = round(
            sum(
                abs(avg_pr_curve[i + 1]["recall"] - avg_pr_curve[i]["recall"])
                * (avg_pr_curve[i + 1]["precision"] + avg_pr_curve[i]["precision"])
                / 2
                for i in range(len(avg_pr_curve) - 1)
            ),
            4,
        )

        max_k = max(len(s["dcg_at_k"]) for s in group)
        avg_dcg_at_k = []
        for k in range(max_k):
            vals = [s["dcg_at_k"][k] for s in group if k < len(s["dcg_at_k"])]
            avg_dcg_at_k.append(round(sum(vals) / len(vals), 4))

        # Average P@k across sessions, aligned by position
        max_pk = max(len(s["precision_at_k"]) for s in group)
        avg_precision_at_k = []
        for k in range(max_pk):
            vals = [
                s["precision_at_k"][k] for s in group if k < len(s["precision_at_k"])
            ]
            avg_precision_at_k.append(round(sum(vals) / len(vals), 4))

        session_means = [sum(s["ratings"]) / len(s["ratings"]) for s in group]
        rating_stats = {
            "mean": round(_stats.mean(session_means), 4),
            "median": round(_stats.median(session_means), 4),
            "std": round(_stats.stdev(session_means), 4)
            if len(session_means) > 1
            else 0.0,
            "min": round(min(session_means), 4),
            "max": round(max(session_means), 4),
            "q1": round(_stats.quantiles(session_means, n=4)[0], 4)
            if len(session_means) >= 4
            else round(_stats.median(session_means), 4),
            "q3": round(_stats.quantiles(session_means, n=4)[2], 4)
            if len(session_means) >= 4
            else round(_stats.median(session_means), 4),
            "session_means": [round(m, 4) for m in session_means],
            "n_sessions": n,
        }

        strategy_results.append(
            {
                "name": name,
                "n_sessions": n,
                "map": round(sum(s["ap"] for s in group) / n, 4),
                "avg_p_at_k": round(sum(s["p_at_k"] for s in group) / n, 4),
                "avg_dcg": round(sum(s["dcg"] for s in group) / n, 4),
                "avg_dcg_at_k": avg_dcg_at_k,
                "avg_precision_at_k": avg_precision_at_k,
                "pr_curve": avg_pr_curve,
                "auc_pr": auc_pr,
                "rating_stats": rating_stats,
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
