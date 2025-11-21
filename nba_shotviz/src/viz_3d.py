"""
3D visualization utilities for the NBA Shot Visualization app.
- Builds and renders the half-court with 3D shot trajectories (Bezier arcs)
"""
import streamlit as st
import plotly.graph_objects as go

from .court_geometry import build_court_figure
from .shots import add_shots_from_df
from .heatmap import (
    zone_diff_grid,
    add_zone_heatmap_surface,
    add_zone_boundaries_from_labels,
    add_zone_hover_markers,  
)

def render_3d_trajectories(
    df,
    league_df=None,
    sample: int = 1000,
    overlay_heatmap: bool = False,
    vlim: float = 0.15,
    force_make_miss_colors: bool = False,

):
    fig = build_court_figure()

    if overlay_heatmap:
        if league_df is None or league_df.empty:
            st.warning("League averages missing; cannot render hot/cold zones.")
        else:
            # heatmap grid + labels + hover text
            X, Y, Zdiff, labels, hover = zone_diff_grid(
                df, league_df, bin_ft=2.0, return_labels=True, return_text=True
            )

            # color surface
            add_zone_heatmap_surface(
                fig, X, Y, Zdiff, vlim=vlim, z_lift=0.01, showscale=True
            )

            # hover markers
            add_zone_hover_markers(fig, X, Y, hover, z_up=0.011)

            # boundaries
            add_zone_boundaries_from_labels(fig, X, Y, labels, z_up=0.09, width=3, halo=True)

        added = add_shots_from_df(
            fig, df, sample=sample,
            release_height_ft=0,
            uniform_color=None if force_make_miss_colors else "#666666",
            width=5, opacity=0.40,
            apex_profile=dict(base=10.0, slope=0.28, lo=13.0, hi=18.5)
        )
        st.caption(f"Rendering {added} shots")

    else:
        added = add_shots_from_df(
            fig, df, sample=sample,
            release_height_ft=0,
            uniform_color=None if force_make_miss_colors else "#666666",
            width=6, opacity=0.55,
            apex_profile=dict(base=10.5, slope=0.30, lo=14.0, hi=19.5)
        )
        st.caption(f"Rendering {added} shots")

    st.plotly_chart(fig, use_container_width=True)
