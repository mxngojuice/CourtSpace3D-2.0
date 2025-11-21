"""
Hot/Cold Zone Heatmap utilities for 3D NBA Shot Visualization.
- Computes FG% difference (player vs. league average) by shot zone.
- Renders color-coded 3D floor surface and zone boundary outlines.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .court_geometry import COURT_LENGTH_HALF, COURT_WIDTH, line3d
from .zone_classify import classify_basic_zone, classify_area_lane
from .zone_tables import league_zone_fg_table, player_zone_fg_table


# collapse ATB areas to LCB
def _collapse_atb_area(area: str) -> str:
    if area in ("Left Side(L)", "Left Side Center(LC)"):
        return "Left Side(L)"
    if area in ("Right Side(R)", "Right Side Center(RC)"):
        return "Right Side(R)"
    return "Center(C)"


def zone_diff_grid(
    player_df: pd.DataFrame,
    league_df: pd.DataFrame,
    bin_ft: float = 2.0,
    return_labels: bool = False,
    return_text: bool = False
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | tuple:
    """
    Build a 2D grid across half-court, assigning each bin the FG% difference
    (player - league average) based on SHOT_ZONE_BASIC × SHOT_ZONE_AREA.

    Returns:
        X, Y, Zdiff, [labels], [hover_text]  (depending on flags)
    """
    # Compute percent by zone
    lg = league_zone_fg_table(league_df).copy()  
    pl = player_zone_fg_table(player_df).copy()  

    #  unfactor back-court three point shots
    bad_areas = ["Back Court(BC)", "None"]
    lg = lg[~lg["SHOT_ZONE_AREA"].isin(bad_areas)].copy()
    pl = pl[~pl["SHOT_ZONE_AREA"].isin(bad_areas)].copy()

    # Collapse ATB areas 
    pl["SHOT_ZONE_AREA"] = pl.apply(
        lambda r: _collapse_atb_area(r["SHOT_ZONE_AREA"]) if r["SHOT_ZONE_BASIC"] == "Above the Break 3"
        else r["SHOT_ZONE_AREA"],
        axis=1
    )
    pl = (
        pl.groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], as_index=False)
          .agg(att=("att", "sum"), made=("made", "sum"))
    )
    pl["player_fg"] = pl.apply(lambda r: (r["made"] / r["att"]) if r["att"] > 0 else 0.0, axis=1)

    lg["SHOT_ZONE_AREA"] = lg.apply(
        lambda r: _collapse_atb_area(r["SHOT_ZONE_AREA"]) if r["SHOT_ZONE_BASIC"] == "Above the Break 3"
        else r["SHOT_ZONE_AREA"],
        axis=1
    )
    lg = (
        lg.groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], as_index=False)
          .agg(league_fg=("league_fg", "mean"))
    )

    # Merge 
    zt = pl.merge(lg, on=["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], how="left")
    zt["league_fg"] = zt["league_fg"].fillna(zt["player_fg"]) 
    zt["diff"] = zt["player_fg"] - zt["league_fg"]

    # Lookups
    zone_to_diff   = {(r["SHOT_ZONE_BASIC"], r["SHOT_ZONE_AREA"]): float(r["diff"])       for _, r in zt.iterrows()}
    zone_to_player = {(r["SHOT_ZONE_BASIC"], r["SHOT_ZONE_AREA"]): float(r["player_fg"])  for _, r in zt.iterrows()}
    zone_to_league = {(r["SHOT_ZONE_BASIC"], r["SHOT_ZONE_AREA"]): float(r["league_fg"])  for _, r in zt.iterrows()}

    # Grid
    x_centers = np.arange(bin_ft / 2, COURT_LENGTH_HALF, bin_ft)
    y_centers = np.arange(-COURT_WIDTH / 2 + bin_ft / 2, COURT_WIDTH / 2, bin_ft)
    X, Y = np.meshgrid(x_centers, y_centers)
    Zdiff  = np.zeros_like(X, dtype=float)
    labels = np.empty_like(X, dtype=object)
    hover_text = np.empty_like(X, dtype=object) if return_text else None

    # Assign
    for i in range(Zdiff.shape[0]):
        for j in range(Zdiff.shape[1]):
            x, y = float(X[i, j]), float(Y[i, j])

            basic = classify_basic_zone(x, y, pad_ft=bin_ft / 2.0)  

            if basic in ("In The Paint (Non-RA)", "Restricted Area"):
                area = "Center(C)"
            else:
                area = classify_area_lane(y)
                if basic == "Above the Break 3":
                    area = _collapse_atb_area(area)

            key = (basic, area)
            diff = zone_to_diff.get(key, 0.0)
            Zdiff[i, j] = diff
            labels[i, j] = f"{basic}_{area}"

            if return_text:
                p = zone_to_player.get(key, float("nan"))
                l = zone_to_league.get(key, float("nan"))
                hover_text[i, j] = (
                    f"<b>{basic}</b> — {area}"
                    f"<br>Player FG%: {p:.1%}"
                    f"<br>League FG%: {l:.1%}"
                    f"<br>Δ: {diff:+.1%}"
                )

    Zdiff = np.nan_to_num(Zdiff, nan=0.0)

    # Return 
    if return_labels and return_text:
        return X, Y, Zdiff, labels, hover_text
    if return_labels:
        return X, Y, Zdiff, labels
    if return_text:
        return X, Y, Zdiff, hover_text
    return X, Y, Zdiff


def add_zone_heatmap_surface(
    fig3d: go.Figure,
    X: np.ndarray,
    Y: np.ndarray,
    Zdiff: np.ndarray,
    vlim: float = 0.15,
    z_lift: float = 0.01,
    showscale: bool = True,
    hover_text: np.ndarray | None = None
):
    """
    Adds a colored surface showing FG% difference vs league average.
    Positive = red (hot), Negative = blue (cold)
    """
    Z = np.full_like(X, z_lift, dtype=float)
    fig3d.add_surface(
        x=X, y=Y, z=Z,
        surfacecolor=Zdiff,
        cmin=-vlim, cmax=vlim,
        colorscale=[
            [0.0, "blue"],
            [0.5, "white"],
            [1.0, "red"]
        ],
        reversescale=False,
        opacity=0.92,
        showscale=showscale,
        text=hover_text if hover_text is not None else None,
        hoverinfo="skip",
        hovertemplate=None,
    )


def add_zone_hover_markers(
    fig3d: go.Figure,
    X: np.ndarray,
    Y: np.ndarray,
    hover_text: np.ndarray,
    *,
    z_up: float = 0.12,    
    size: int = 14,        
    opacity: float = 0.02, 
    densify: bool = True,   
):
    """
    Adds an 'invisible' hover layer over the heatmap.
    - Places markers high enough to avoid occlusion by surface/lines.
    - Optionally densifies each cell (center + 4 neighbors) to enlarge the hit area.
    """
 
    fig3d.update_layout(hovermode="closest")

    xc = X.ravel()
    yc = Y.ravel()
    txt = hover_text.ravel().tolist()

    if densify:
        # Estimate bin size 
        x_cent = X[0, :]
        y_cent = Y[:, 0]
        dx = float(np.median(np.diff(x_cent))) if x_cent.size > 1 else 2.0
        dy = float(np.median(np.diff(y_cent))) if y_cent.size > 1 else 2.0
        # Offsets 
        offs = [(0.0, 0.0), (dx*0.33, 0.0), (-dx*0.33, 0.0), (0.0, dy*0.33), (0.0, -dy*0.33)]

        xs, ys, texts = [], [], []
        for (ox, oy) in offs:
            xs.append(xc + ox)
            ys.append(yc + oy)
            texts.append(txt)
        xs = np.concatenate(xs)
        ys = np.concatenate(ys)
        texts = sum(texts, [])  
    else:
        xs, ys, texts = xc, yc, txt

    fig3d.add_trace(go.Scatter3d(
        x=xs,
        y=ys,
        z=np.full(xs.shape, z_up),
        mode="markers",
        marker=dict(
            size=size,          
            opacity=opacity,   
            color="black",      
            line=dict(width=0),
        ),
        text=texts,
        hoverinfo="text",
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
    ))


def add_zone_boundaries_from_labels(
    fig3d: go.Figure,
    X: np.ndarray,
    Y: np.ndarray,
    labels: np.ndarray,
    z_up: float = 0.08,
    width: int = 3,
    color: str = "black",
    halo: bool = True,
    halo_width_extra: int = 3,
    halo_color: str = "white",
    halo_opacity: float = 1.0
):
    """
    Draw crisp zone outlines by comparing neighbor cells and plotting
    segments along the *bin edges* (not centers).

    Visual clarity improvement:
      - Optionally draw a white "halo" under each black boundary so lines read
        clearly over both hot (red) and cold (blue) regions.
    """
    # bin centers
    x_cent = X[0, :]    # shape (nx,)
    y_cent = Y[:, 0]    # shape (ny,)

    # bin size
    dx = float(np.median(np.diff(x_cent))) if x_cent.size > 1 else 2.0
    dy = float(np.median(np.diff(y_cent))) if y_cent.size > 1 else 2.0

    # edges
    x_edges = np.concatenate(([x_cent[0] - dx/2], (x_cent[:-1] + x_cent[1:]) / 2, [x_cent[-1] + dx/2]))
    y_edges = np.concatenate(([y_cent[0] - dy/2], (y_cent[:-1] + y_cent[1:]) / 2, [y_cent[-1] + dy/2]))

    ny, nx = labels.shape

    def _add_segment(x0, x1, y0, y1):
        # optional halo 
        if halo:
            fig3d.add_trace(
                line3d([x0, x1], [y0, y1], [z_up, z_up],
                       width=width + halo_width_extra, color=halo_color, opacity=halo_opacity)
            )
        # main boundary 
        fig3d.add_trace(
            line3d([x0, x1], [y0, y1], [z_up, z_up],
                   width=width, color=color, opacity=1.0)
        )

    # vertical boundaries
    for i in range(ny):
        y0, y1 = y_edges[i], y_edges[i+1]
        for j in range(nx - 1):
            if labels[i, j] != labels[i, j+1]:
                xe = x_edges[j+1]
                _add_segment(xe, xe, y0, y1)

    #horizontal boundaries
    for i in range(ny - 1):
        ye = y_edges[i+1]
        for j in range(nx):
            if labels[i, j] != labels[i+1, j]:
                x0, x1 = x_edges[j], x_edges[j+1]
                _add_segment(x0, x1, ye, ye)
