"""
Shot coordinate transforms + Bezier trajectory arcs for 3D NBA visualization.
- Supports configurable apex profile and optional uniform arc color.
"""

from typing import Optional, Dict
import numpy as np
import plotly.graph_objects as go

from .court_geometry import HOOP_X, HOOP_Y, RIM_HEIGHT

INCHES_TO_FEET = 1 / 10.0

def nba_shot_to_court_xy(loc_x_in, loc_y_in):
    """Convert nba_api LOC_X/LOC_Y (inches, hoop-centered) -> (x,y) feet in our baseline frame."""
    x_ft = HOOP_X + loc_y_in * INCHES_TO_FEET   # forward from baseline
    y_ft = loc_x_in * INCHES_TO_FEET            # lateral, centered on hoop
    return float(x_ft), float(y_ft)

def _apex_by_distance(
    x0: float, y0: float, x1: float = HOOP_X, y1: float = HOOP_Y,
    *, base: float = 10.5, slope: float = 0.30, lo: float = 14.0, hi: float = 19.5
) -> float:
    """
    Parametric apex model (feet). Height grows with horizontal distance.
    - base: baseline height
    - slope: ft of height per ft of horizontal distance
    - lo/hi: clamps
    """
    d = float(np.hypot(x1 - x0, y1 - y0))
    apex = base + slope * d
    return float(np.clip(apex, lo, hi))

def add_shot_arc(
    fig,
    x0: float, y0: float,
    z0: float = 1.5,
    x1: float = HOOP_X, y1: float = HOOP_Y, z1: float = RIM_HEIGHT,
    apex_z: float = 18.0,
    n: int = 160,
    color: str = "#1f77b4",
    width: int = 6,
    opacity: float = 0.45,
    hovertext: Optional[str] = None,
):
    """Quadratic Bezier arc from (x0,y0,z0) to rim with peak ~ apex_z."""
    z_m = 2 * apex_z - 0.5 * (z0 + z1)  # ensures t=0.5 ~ apex_z

    xm, ym = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    t = np.linspace(0.0, 1.0, n)

    x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * xm + t ** 2 * x1
    y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ym + t ** 2 * y1
    z = (1 - t) ** 2 * z0 + 2 * (1 - t) * t * z_m + t ** 2 * z1

    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode="lines",
        line=dict(width=width, color=color),
        opacity=opacity,
        showlegend=False,
        hoverinfo="text" if hovertext else "skip",
        hovertext=[hovertext] * len(x) if hovertext else None,
    ))

def add_shots_from_df(
    fig,
    df,
    sample: Optional[int] = None,
    release_height_ft: float = 1.5,
    make_bonus: float = 0.0,
    uniform_color: Optional[str] = None,
    width: int = 6,
    opacity: float = 0.45,
    apex_profile: Optional[Dict[str, float]] = None,
) -> int:
    """
    Draw arcs for each shot.
    - If `uniform_color` is provided, use it for all arcs (e.g., heatmap mode).
      Otherwise, color by make/miss (green/red).
    - `apex_profile` may include base, slope, lo, hi for _apex_by_distance.
    """
    if df is None or len(df) == 0:
        return 0
    if {"LOC_X", "LOC_Y"}.difference(df.columns):
        return 0

    if sample and len(df) > sample:
        df = df.sample(sample, random_state=7)

    # defaults if not provided
    ap = apex_profile or dict(base=10.5, slope=0.30, lo=14.0, hi=19.5)

    n = 0
    for _, row in df.iterrows():
        x0, y0 = nba_shot_to_court_xy(row["LOC_X"], row["LOC_Y"])

        made = bool(row.get("SHOT_MADE_FLAG", 0))
        apex = _apex_by_distance(x0, y0, **ap) + (make_bonus if made else 0.0)

        if uniform_color:
            color = uniform_color
        else:
            color = "#2ca02c" if made else "#d62728"


        # hover text
        action = row.get("ACTION_TYPE", "Unknown")
        dist   = row.get("SHOT_DISTANCE", None)

        made = bool(row.get("SHOT_MADE_FLAG", 0))
        result = "MAKE" if made else "MISS"

        hover = f"{action} · {dist} · {result}"


        add_shot_arc(
            fig, x0, y0,
            z0=release_height_ft,
            apex_z=apex,
            color=color,
            width=width,
            opacity=opacity,
            hovertext=hover,
        )
        n += 1
    return n
