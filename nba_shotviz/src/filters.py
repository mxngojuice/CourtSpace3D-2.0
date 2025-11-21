"""
Filtering utilities for the Streamlit 3D NBA Shot Visualization app.
- Default filter state
- Period-only filtering (no Home/Away for now)
"""

import pandas as pd

def default_filter_state() -> dict:
    """
    Returns a default filter state used by Streamlit sidebar widgets.
    Note: 'context' is kept for forward-compatibility but is unused.
    """
    return {
        "player": None,
        "season": None,
        "opponent": None,
        "periods": [1, 2, 3, 4, 5],
        "context": [],   # unused for now
        "sample": 1000,
        "result": "All", 
        "venue": "All", 
        "action_type": "All",  
        # "clutch_only": False,
    }


def filter_df(df: pd.DataFrame, state: dict) -> pd.DataFrame:
    """
    Apply period-only filtering.
    """
    out = df.copy()

    # Period filter 
    if state.get("periods") and "PERIOD" in out.columns:
        out = out[out["PERIOD"].isin(state["periods"])]

    # Make/Miss filter 
    if state.get("result") in ("Makes", "Misses") and "SHOT_MADE_FLAG" in out.columns:
        want = 1 if state["result"] == "Makes" else 0
        out = out[out["SHOT_MADE_FLAG"] == want]

    # Home/Away filter 
    if state.get("venue") in ("Home", "Away") and "VENUE" in out.columns:
        out = out[out["VENUE"] == state["venue"]]

    # Opponent filter 
    if state.get("opponent") not in (None, "All") and "OPPONENT" in out.columns:
        out = out[out["OPPONENT"] == state["opponent"]]

    # Action Type filter
    if state.get("action_type") not in (None, "All") and "ACTION_TYPE" in out.columns:
        out = out[out["ACTION_TYPE"] == state["action_type"]]

    # Shot Distance filter
    if state.get("shot_distance") and "SHOT_DISTANCE" in out.columns:
        lo, hi = state["shot_distance"]
        out = out[(out["SHOT_DISTANCE"] >= lo) & (out["SHOT_DISTANCE"] <= hi)]

    # # Clutch filter 
    # if state.get("clutch_only") and "CLUTCH" in out.columns:
    #     out = out[out["CLUTCH"]]


    return out
