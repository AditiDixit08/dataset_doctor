"""score.py - turns a list of issues into a 0-100 health score."""

PENALTY = {"high": 10, "medium": 4, "low": 1}


def health_score(issues):
    """Start at 100, subtract points for every issue, never go below 0."""
    total = sum(PENALTY[i["severity"]] for i in issues)
    return max(0, 100 - total)


def category_scores(issues):
    """A separate 0-100 score for each type of issue (missing, outliers...)."""
    totals = {}
    for i in issues:
        totals[i["type"]] = totals.get(i["type"], 0) + PENALTY[i["severity"]]
    return {kind: max(0, 100 - pts) for kind, pts in totals.items()}