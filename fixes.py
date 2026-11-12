"""fixes.py - the ONLY actions the app is allowed to run.
The AI can only pick a name from this list. It can never run its own code."""
import pandas as pd


def drop_duplicates(df, col=None):
    return df.drop_duplicates().reset_index(drop=True)


def impute_median(df, col):
    df = df.copy()
    df[col] = df[col].fillna(df[col].median())
    return df


def impute_mode(df, col):
    df = df.copy()
    mode = df[col].mode()
    if len(mode) > 0:
        df[col] = df[col].fillna(mode[0])
    return df


def drop_column(df, col):
    return df.drop(columns=[col])


def cap_outliers(df, col):
    """Clip extreme values to the IQR fences instead of deleting rows."""
    df = df.copy()
    q1, q3 = df[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    df[col] = df[col].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    return df


def cast_numeric(df, col):
    df = df.copy()
    df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def standardize_case(df, col):
    df = df.copy()
    cleaned = df[col].astype(str).str.strip().str.lower()
    df[col] = df[col].where(df[col].isna(), cleaned)
    return df


# Name -> function. This dictionary is the whitelist.
ACTIONS = {
    "drop_duplicates": drop_duplicates,
    "standardize_case": standardize_case,
    "cast_numeric": cast_numeric,
    "impute_median": impute_median,
    "impute_mode": impute_mode,
    "cap_outliers": cap_outliers,
    "drop_column": drop_column,
}

# Safe order to apply fixes in (smaller number = earlier)
PRIORITY = {
    "drop_duplicates": 0,
    "standardize_case": 1,
    "cast_numeric": 2,
    "impute_median": 3,
    "impute_mode": 3,
    "cap_outliers": 4,
    "drop_column": 5,
}


def apply_fix(df, action, column):
    if action not in ACTIONS:
        raise ValueError(f"Unknown action: {action}")
    return ACTIONS[action](df, column)