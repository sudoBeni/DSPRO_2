import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app.analytics import FEEDBACK_FILE, get_analytics

if not FEEDBACK_FILE.exists():
    print(f"feedback.jsonl not found at: {FEEDBACK_FILE.resolve()}", file=sys.stderr)
    sys.exit(1)

data = get_analytics()
overall = data["overall"]
strategies = [s for s in data["strategies"] if s["n_sessions"] > 0]

SEP = "-" * 60


def section(title: str) -> None:
    print(SEP)
    print(title)
    print(SEP)


# -- Overall summary ----------------------------------------------------------
section("OVERALL")
print(f"sessions,        {overall['n_sessions']}")
print(f"MAP,             {overall['map']:.4f}")
print(f"avg_precision@k, {overall['avg_p_at_k']:.4f}")
print()


# -- Scalar metric tables -----------------------------------------------------
def ranked_table(title: str, key: str) -> None:
    section(title)
    print(f"{'rank':<6}, {'recommender':<18}, {'value':>7}, {'n':>3}")
    ranked = sorted(strategies, key=lambda s: s[key] or 0, reverse=True)
    for i, s in enumerate(ranked, 1):
        print(f"{i:<6}, {s['name']:<18}, {s[key]:>7.4f}, {s['n_sessions']:>3}")
    print()


ranked_table("MAP (Mean Average Precision)", "map")
ranked_table("Avg Precision@10", "avg_p_at_k")
ranked_table("Avg DCG (Discounted Cumulative Gain)", "avg_dcg")
ranked_table("AUC-PR (Area Under PR Curve)", "auc_pr")

# -- Rating stats -------------------------------------------------------------
section("Rating Stats (scale 1-4, relevant >= 3)")
print(
    f"{'recommender':<18}, {'n':>3}, {'mean':>6}, {'median':>6}, {'std':>5}, {'min':>4}, {'Q1':>4}, {'Q3':>4}, {'max':>4}"
)
rated = sorted(
    strategies,
    key=lambda s: s["rating_stats"]["mean"] if s["rating_stats"] else 0,
    reverse=True,
)
for s in rated:
    rs = s["rating_stats"]
    if not rs:
        continue
    print(
        f"{s['name']:<18}, {rs['n_sessions']:>3}, {rs['mean']:>6.3f}, {rs['median']:>6.3f}, {rs['std']:>5.3f}, {rs['min']:>4.2f}, {rs['q1']:>4.2f}, {rs['q3']:>4.2f}, {rs['max']:>4.2f}"
    )
print()

# -- Precision@k grid ---------------------------------------------------------
max_k = max(len(s["avg_precision_at_k"]) for s in strategies)
k_headers = ", ".join(f"p@{k+1}" for k in range(max_k))
section("Precision@k by rank position")
print(f"{'recommender':<18}, {k_headers}")
for s in strategies:
    vals = ", ".join(f"{v:.4f}" for v in s["avg_precision_at_k"])
    print(f"{s['name']:<18}, {vals}")
print()

# -- DCG@k grid ---------------------------------------------------------------
k_headers_dcg = ", ".join(f"dcg@{k+1}" for k in range(max_k))
section("DCG@k cumulative by rank position")
print(f"{'recommender':<18}, {k_headers_dcg}")
for s in strategies:
    vals = ", ".join(f"{v:.4f}" for v in s["avg_dcg_at_k"])
    print(f"{s['name']:<18}, {vals}")
print()

# -- Session means ------------------------------------------------------------
section("Session means (per-session avg rating)")
for s in strategies:
    rs = s["rating_stats"]
    if not rs:
        continue
    vals = ", ".join(f"{v:.2f}" for v in rs["session_means"])
    print(f"{s['name']:<18}, {vals}")
