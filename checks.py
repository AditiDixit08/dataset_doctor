"""checks.py - the 'medical tests'. Each check returns a list of issues."""
import numpy as np
import pandas as pd
from scipy import stats


def make_issue(kind, column, severity, detail):
    """Every problem we find is stored in this same simple shape."""
    return {"type": kind, "column": column, "severity": severity, "detail": detail}


def is_id_like(series):
    """True if almost every value is unique and the column is not a decimal."""
    if pd.api.types.is_float_dtype(series):
        return False
    return len(series) > 1 and series.nunique() / len(series) > 0.95


# ---------- 1. Missing values ----------
def check_missing(df):
    issues = []
    for col in df.columns:
        pct = df[col].isna().mean()
        if pct == 0:
            continue
        if pct > 0.30:
            severity = "high"
        elif pct > 0.05:
            severity = "medium"
        else:
            severity = "low"
        issues.append(make_issue("missing", col, severity, f"{pct:.1%} values missing"))
    return issues


# ---------- 2. Duplicate rows ----------
def check_duplicates(df):
    n_dup = int(df.duplicated().sum())
    if n_dup == 0:
        return []
    pct = n_dup / len(df)
    severity = "high" if pct > 0.05 else "medium" if pct > 0.01 else "low"
    return [make_issue("duplicates", "ALL", severity, f"{n_dup} duplicate rows ({pct:.1%})")]


# ---------- 3. Outliers (IQR rule) ----------
def check_outliers(df):
    issues = []
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if len(s) < 10 or is_id_like(s):
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        pct = ((s < low) | (s > high)).mean()
        if pct == 0:
            continue
        severity = "high" if pct > 0.10 else "medium" if pct > 0.02 else "low"
        detail = f"{pct:.1%} values outside [{low:.1f}, {high:.1f}]"
        issues.append(make_issue("outliers", col, severity, detail))
    return issues


# ---------- 4. Suspicious columns ----------
def check_suspicious(df):
    issues = []

    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            continue

        # (a) Constant column: the same value in every row
        if s.nunique() == 1:
            issues.append(make_issue("constant", col, "medium", "same value in every row"))
            continue

        # (b) ID-like column: unique per row, useless for analysis
        if is_id_like(df[col]):
            issues.append(make_issue("id_like", col, "low",
                                     "almost every value is unique (looks like an ID)"))

        # Checks (c) and (d) only make sense for text columns
        if df[col].dtype == object or str(df[col].dtype) in ("string", "str"):
            # (c) Numbers stored as text
            as_num = pd.to_numeric(s, errors="coerce")
            if as_num.notna().mean() > 0.90:
                issues.append(make_issue("text_numbers", col, "medium",
                                         "numbers stored as text"))
                continue

            # (d) Inconsistent casing / spaces: 'Pune', 'pune', ' Pune'
            text = s.astype(str)
            if text.str.strip().str.lower().nunique() < text.nunique():
                issues.append(make_issue("casing", col, "medium",
                                         "same value in different cases or spacing"))

    # (e) Highly correlated pairs: two columns saying the same thing
    num = df.select_dtypes(include="number")
    num = num.loc[:, [c for c in num.columns if not is_id_like(num[c])]]
    if num.shape[1] >= 2:
        corr = num.corr().abs()
        cols = list(corr.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                if corr.iloc[i, j] > 0.95:
                    issues.append(make_issue("correlated", f"{cols[i]} & {cols[j]}", "medium",
                                             f"correlation = {corr.iloc[i, j]:.2f}"))
    return issues


# ---------- 5. Drift ----------
def check_drift(df, sort_col=None):
    """Compare the first half of the data with the second half."""
    issues = []
    data = df.sort_values(sort_col) if sort_col else df
    half = len(data) // 2
    if half < 30:
        return issues

    labels = np.where(np.arange(len(data)) < half, "first", "second")
    first, second = data.iloc[:half], data.iloc[half:]

    for col in data.columns:
        if col == sort_col or is_id_like(data[col]):
            continue

        if pd.api.types.is_numeric_dtype(data[col]):
            a, b = first[col].dropna(), second[col].dropna()
            if len(a) < 30 or len(b) < 30:
                continue
            stat, p = stats.ks_2samp(a, b)
            if p < 0.01:
                severity = "high" if stat > 0.20 else "medium"
            elif p < 0.05:
                severity = "low"
            else:
                continue
            detail = f"distribution shifted (KS={stat:.2f}, p={p:.4f})"
            issues.append(make_issue("drift", col, severity, detail))

        elif data[col].nunique() <= 20:
            table = pd.crosstab(data[col].fillna("MISSING"), labels)
            if table.shape[0] < 2 or table.shape[1] < 2:
                continue
            chi2, p, _, _ = stats.chi2_contingency(table)
            if p < 0.01:
                severity = "medium"
            elif p < 0.05:
                severity = "low"
            else:
                continue
            detail = f"category mix changed (p={p:.4f})"
            issues.append(make_issue("drift", col, severity, detail))
    return issues


# ---------- Run everything ----------
def run_all_checks(df, sort_col=None):
    issues = []
    issues += check_missing(df)
    issues += check_duplicates(df)
    issues += check_outliers(df)
    issues += check_suspicious(df)
    issues += check_drift(df, sort_col)
    return issues