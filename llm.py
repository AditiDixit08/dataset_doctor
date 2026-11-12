"""llm.py - asks Claude for fix suggestions. Falls back to simple rules
if there is no API key, so the app always works."""
import json
import os

import pandas as pd

from fixes import ACTIONS, PRIORITY

MODEL = "claude-sonnet-5-5"

SYSTEM = (
    "You are a careful data-cleaning assistant. "
    "Return ONLY a JSON list, with no extra text and no markdown. "
    'Each item must look like {"action": "...", "column": "...", "reason": "..."}. '
    "Allowed actions: " + ", ".join(ACTIONS) + ". "
    'Use column "ALL" for drop_duplicates. '
    "Only suggest fixes that address the listed issues."
)


def build_summary(df, issues):
    """Send a SMALL summary to the AI, never the whole dataset (privacy + cost)."""
    summary = {
        "rows": len(df),
        "columns": {c: str(t) for c, t in df.dtypes.items()},
        "issues": issues[:40],
        "sample_rows": df.head(5).astype(str).to_dict(orient="records"),
    }
    return json.dumps(summary, indent=2)


def parse_json(text):
    """Claude sometimes wraps its JSON in markdown code fences. Remove them."""
    fence = chr(96) * 3
    text = text.strip()
    if text.startswith(fence):
        text = text.strip(chr(96))
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def validate(items, df):
    """Keep only suggestions that use a real action and a real column."""
    good = []
    for item in items:
        action, col = item.get("action"), item.get("column")
        if action not in ACTIONS:
            continue
        if action != "drop_duplicates" and col not in df.columns:
            continue
        good.append({"action": action, "column": col,
                     "reason": str(item.get("reason", "")), "source": "Claude"})
    return good


def suggest_with_claude(df, issues):
    import anthropic
    client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY automatically
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_summary(df, issues)}],
    )
    return validate(parse_json(msg.content[0].text), df)


def suggest_offline(df, issues):
    """Simple rules: one fix per issue type."""
    out, seen = [], set()

    def add(action, col, reason):
        if (action, col) not in seen:
            seen.add((action, col))
            out.append({"action": action, "column": col, "reason": reason, "source": "Rules"})

    for i in issues:
        kind, col = i["type"], i["column"]
        if kind == "missing":
            if i["severity"] == "high":
                add("drop_column", col, "more than 30% missing")
            elif pd.api.types.is_numeric_dtype(df[col]):
                add("impute_median", col, "fill gaps with the median")
            else:
                add("impute_mode", col, "fill gaps with the most common value")
        elif kind == "duplicates":
            add("drop_duplicates", "ALL", "remove repeated rows")
        elif kind == "outliers":
            add("cap_outliers", col, "clip extreme values")
        elif kind == "constant":
            add("drop_column", col, "same value in every row")
        elif kind == "text_numbers":
            add("cast_numeric", col, "convert text to numbers")
        elif kind == "casing":
            add("standardize_case", col, "make spelling consistent")
    return out


def suggest_fixes(df, issues):
    if not issues:
        return []
    items = None
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            items = suggest_with_claude(df, issues)
        except Exception as e:
            print("Claude failed, using offline rules:", e)
    if not items:
        items = suggest_offline(df, issues)
    return sorted(items, key=lambda s: PRIORITY[s["action"]])