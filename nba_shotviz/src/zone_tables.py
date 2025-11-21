"""
Zone-level FG% tables for player and league.

- player_zone_fg_table(player_df): returns columns:
    SHOT_ZONE_BASIC, SHOT_ZONE_AREA, player_fg, att, made

- league_zone_fg_table(league_df): returns columns:
    SHOT_ZONE_BASIC, SHOT_ZONE_AREA, league_fg

Both functions are defensive about upstream schemas from nba_api.
"""

import pandas as pd


def _safe_ratio(numer, denom):
    numer = float(numer)
    denom = float(denom)
    return (numer / denom) if denom > 0 else 0.0


def player_zone_fg_table(player_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate player shots into zone-level FG%.
    Expects columns:
        SHOT_ZONE_BASIC, SHOT_ZONE_AREA, SHOT_MADE_FLAG  (0/1)
    """
    required = {"SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"}
    if not required.issubset(player_df.columns):
        raise ValueError(f"player_df missing required columns: {required - set(player_df.columns)}")

    has_flag = "SHOT_MADE_FLAG" in player_df.columns
    if not has_flag:
        player_df = player_df.assign(SHOT_MADE_FLAG=0)

    g = (
        player_df
        .groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], dropna=False, as_index=False)
        .agg(att=("SHOT_MADE_FLAG", "size"),
             made=("SHOT_MADE_FLAG", "sum"))
    )

    g["player_fg"] = g.apply(lambda r: _safe_ratio(r["made"], r["att"]), axis=1)
    return g[["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "player_fg", "att", "made"]]


def league_zone_fg_table(league_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate league averages into zone-level FG%.
    Accepts either:
      - one row per shot with SHOT_MADE_FLAG (rare), OR
      - pre-aggregated rows with FGA/FGM and/or FG_PCT (common for league averages).
    Expects columns (any of these combos):
        - SHOT_ZONE_BASIC, SHOT_ZONE_AREA, FGA, FGM
        - SHOT_ZONE_BASIC, SHOT_ZONE_AREA, FG_PCT
        - SHOT_ZONE_BASIC, SHOT_ZONE_AREA, SHOT_MADE_FLAG  (one row per shot)
    """
    required = {"SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"}
    if not required.issubset(league_df.columns):
        raise ValueError(f"league_df missing required columns: {required - set(league_df.columns)}")

    cols = set(league_df.columns)

    if {"FGM", "FGA"}.issubset(cols):
        # Pre-aggregated table present
        g = (
            league_df
            .groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], dropna=False, as_index=False)
            .agg(FGM=("FGM", "sum"), FGA=("FGA", "sum"))
        )
        g["league_fg"] = g.apply(lambda r: _safe_ratio(r["FGM"], r["FGA"]), axis=1)
        return g[["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "league_fg"]]

    if "FG_PCT" in cols:
        # Prefer weighting by attempts if FGA exists
        if "FGA" in cols:
            g = (
                league_df
                .groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], dropna=False, as_index=False)
                .apply(lambda df: pd.Series({
                    "league_fg": (df["FG_PCT"] * df["FGA"]).sum() / max(df["FGA"].sum(), 1.0)
                }))
                .reset_index(drop=True)
            )
        else:
            g = (
                league_df
                .groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], dropna=False, as_index=False)
                .agg(league_fg=("FG_PCT", "mean"))
            )
        return g[["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "league_fg"]]

    if "SHOT_MADE_FLAG" in cols:
        # One row per shot - compute percent directly
        g = (
            league_df
            .groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"], dropna=False, as_index=False)
            .agg(att=("SHOT_MADE_FLAG", "size"),
                 made=("SHOT_MADE_FLAG", "sum"))
        )
        g["league_fg"] = g.apply(lambda r: _safe_ratio(r["made"], r["att"]), axis=1)
        return g[["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "league_fg"]]

    return pd.DataFrame(columns=["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "league_fg"])
