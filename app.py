"""app.py - the screen the user sees. Run with: streamlit run app.py"""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from checks import run_all_checks
from fixes import apply_fix
from llm import suggest_fixes
from score import category_scores, health_score

st.set_page_config(page_title="Dataset Doctor", layout="wide")
st.title("Dataset Doctor")
st.caption("Upload a CSV. Get a health score. Fix problems with one click.")


def gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, title={"text": title},
        gauge={"axis": {"range": [0, 100]},
               "steps": [{"range": [0, 50], "color": "#f4c7c3"},
                         {"range": [50, 80], "color": "#fce8b2"},
                         {"range": [80, 100], "color": "#b7e1cd"}]}))
    fig.update_layout(height=260, margin=dict(t=60, b=10, l=20, r=20))
    return fig


# ---------- Step 1: upload ----------
file = st.file_uploader("Upload a CSV file", type="csv")
if file is None:
    st.info("Upload a CSV to start.")
    st.stop()

# session_state is the app's memory between clicks
if st.session_state.get("filename") != file.name:
    original = pd.read_csv(file)
    st.session_state.filename = file.name
    st.session_state.original = original
    st.session_state.df = original.copy()
    st.session_state.suggestions = None
    st.session_state.log = []
    st.session_state.original_score = health_score(run_all_checks(original))

# ---------- Step 2: run the checks ----------
sort_choice = st.sidebar.selectbox(
    "Column that orders the data in time (for drift)",
    ["(row order)"] + list(st.session_state.df.columns))
sort_col = None if sort_choice == "(row order)" else sort_choice

df = st.session_state.df
issues = run_all_checks(df, sort_col)
score = health_score(issues)

tab1, tab2, tab3, tab4 = st.tabs(["Issues", "Drift", "Fixes", "Report"])

# ---------- Tab 1: issues ----------
with tab1:
    left, right = st.columns([1, 2])
    left.plotly_chart(gauge(score, "Health score"))
    cats = category_scores(issues)
    if cats:
        bar = go.Figure(go.Bar(x=list(cats.keys()), y=list(cats.values())))
        bar.update_layout(height=260, yaxis=dict(range=[0, 100]), title="Score by category")
        right.plotly_chart(bar)
    if issues:
        st.dataframe(pd.DataFrame(issues), hide_index=True)
    else:
        st.success("No issues found. Healthy dataset!")

# ---------- Tab 2: drift ----------
with tab2:
    drift = [i for i in issues if i["type"] == "drift"]
    st.write("Compares the first half of the rows with the second half.")
    if drift:
        st.dataframe(pd.DataFrame(drift), hide_index=True)
    else:
        st.success("No drift detected.")

# ---------- Tab 3: fixes ----------
with tab3:
    if st.button("Get fix suggestions"):
        st.session_state.suggestions = suggest_fixes(df, issues)

    suggestions = st.session_state.suggestions
    if suggestions:
        st.caption(f"Suggestions from: {suggestions[0]['source']}")
        st.write("Tick the fixes you approve:")
        for i, s in enumerate(suggestions):
            st.checkbox(f"{s['action']} on {s['column']}: {s['reason']}",
                        value=True, key=f"fix_{i}")

        if st.button("Apply selected fixes"):
            new_df = st.session_state.df
            for i, s in enumerate(suggestions):
                if st.session_state.get(f"fix_{i}"):
                    try:
                        new_df = apply_fix(new_df, s["action"], s["column"])
                        st.session_state.log.append(s)
                    except Exception as e:
                        st.warning(f"Skipped {s['action']} on {s['column']}: {e}")
            st.session_state.df = new_df
            st.session_state.suggestions = None
            for key in [k for k in st.session_state if k.startswith("fix_")]:
                del st.session_state[key]
            st.rerun()
    elif st.session_state.suggestions is not None:
        st.success("Nothing to fix.")

# ---------- Tab 4: report ----------
with tab4:
    c1, c2 = st.columns(2)
    c1.metric("Health score before", st.session_state.original_score)
    c2.metric("Health score after", score, delta=score - st.session_state.original_score)
    st.write(f"Rows: {len(st.session_state.original)} before, {len(df)} after. "
             f"Columns: {st.session_state.original.shape[1]} before, {df.shape[1]} after.")
    st.write(f"Fixes applied: {len(st.session_state.log)}")
    st.download_button("Download cleaned CSV", df.to_csv(index=False).encode("utf-8"),
                       "cleaned.csv", "text/csv")
    st.download_button("Download fix log (JSON)",
                       json.dumps(st.session_state.log, indent=2),
                       "fix_log.json", "application/json")