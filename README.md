Dataset Doctor
==============

Upload any CSV and get a 0-100 data health score. Dataset Doctor finds the problems, suggests fixes, and cleans the data after you approve each one.

Live demo: https://datasetdoctor-i6gwxkdxudurr553r5a93b.streamlit.app/


What it checks
--------------

| Check | How it works |
|-------|--------------|
| Missing values | Percentage of empty cells per column |
| Duplicates | Repeated rows |
| Outliers | IQR rule (values outside 1.5 x IQR) |
| Suspicious columns | Constant columns, ID-like columns, numbers stored as text, inconsistent casing, near-identical (correlated) columns |
| Drift | Compares first half vs second half of the data using the KS test (numbers) and chi-square test (categories) |

How it works
------------

1. Upload a CSV.
2. The tool runs all checks and calculates a health score.
3. An AI assistant (Claude) suggests fixes. If no API key is set, built-in rules are used instead.
4. You tick the fixes you approve and click Apply.
5. See the before vs after score, then download the cleaned CSV and a fix log.

Safety by design
----------------

The AI can only choose from 7 approved cleaning actions: drop_duplicates, standardize_case, cast_numeric, impute_median, impute_mode, cap_outliers, drop_column. It never writes or runs its own code. Every suggestion is also checked against real column names before it is shown.

Only a small summary (column types, issues, 5 sample rows) is sent to the AI, never the full dataset.

Results
-------

Practice dataset with planted problems (1,040 rows):

| Measure | Before | After |
|---------|--------|-------|
| Health score | 38 | 87 |
| Rows | 1,040 | 1,000 |
| Columns | 9 | 7 |

Real datasets:

| Dataset | Issues found | Score before | Score after |
|---------|--------------|--------------|-------------|
| Titanic | | | |
| Telco Churn | | | |
| Superstore | | | |

Tech stack
----------

Python, pandas, SciPy, Plotly, Streamlit, Claude API

Project structure
-----------------

    checks.py             the data-quality checks
    score.py              health score calculation
    fixes.py              the 7 approved cleaning actions
    llm.py                AI suggestions with rule-based fallback
    app.py                Streamlit web app
    make_sample_data.py   builds a practice dataset with planted problems

Run locally
-----------

    pip install -r requirements.txt
    python make_sample_data.py
    streamlit run app.py


Limitations
-----------

- Severity weights and thresholds are fixed design choices and can be tuned.
- Drift is only meaningful when rows are in time order (pick a date column in the sidebar).
- Filling missing values can hide real patterns, so review fixes before applying them.

Author
------

Aditi Dixit
