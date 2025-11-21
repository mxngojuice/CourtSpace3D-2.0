"""
Data access helpers for Streamlit app:
- Active players (cached)
- Seasons list (cached)
- Shot log loader via nba_api (cached)
"""

import pandas as pd
import streamlit as st
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import shotchartdetail


# Single cached raw list of dictionaries for each player
@st.cache_data(show_spinner=False)
def get_players_raw():
    # all players ever, not just active
    return players.get_players()

@st.cache_data(show_spinner=False)
def get_available_players():
    return sorted([p["full_name"] for p in get_players_raw()])

@st.cache_data(show_spinner=False)
def get_name_to_id():
    return {p["full_name"]: p["id"] for p in get_players_raw()}

# Seasons 
@st.cache_data(show_spinner=False)
def get_available_seasons(start: int = 1996, end: int = 2025):
    return [f"{y}-{str(y+1)[-2:]}" for y in range(start, end)]

# Teams
@st.cache_data(show_spinner=False)
def get_team_maps():
    tlst = teams.get_teams()
    id2abbr  = {t["id"]: t["abbreviation"] for t in tlst}
    abbr2full= {t["abbreviation"]: t["full_name"] for t in tlst}
    id2full  = {t["id"]: t["full_name"] for t in tlst}
    return id2abbr, abbr2full, id2full

def _attach_venue_and_opponent(player_df: pd.DataFrame) -> pd.DataFrame:

    if player_df.empty:
        return player_df

    id2abbr, abbr2full, _ = get_team_maps()

    df = player_df.copy()
    df["TEAM_ABBR"] = df["TEAM_ID"].map(id2abbr)

    # Venue
    venue = pd.Series("Unknown", index=df.index)
    venue = venue.mask(df["TEAM_ABBR"].eq(df["HTM"]), "Home")
    venue = venue.mask(df["TEAM_ABBR"].eq(df["VTM"]), "Away")
    df["VENUE"] = venue

    # Opponent (abbr + full)
    opp_abbr = pd.Series(pd.NA, index=df.index)
    opp_abbr = opp_abbr.mask(df["VENUE"].eq("Home"), df["VTM"])
    opp_abbr = opp_abbr.mask(df["VENUE"].eq("Away"), df["HTM"])
    df["OPPONENT_ABBR"] = opp_abbr
    df["OPPONENT"] = df["OPPONENT_ABBR"].map(abbr2full)

    return df

# Shot log loader
@st.cache_data(show_spinner=True)
def load_shotlog(player_name: str, season: str) -> pd.DataFrame:
    """
    Returns a DataFrame with at least columns:
      ['LOC_X','LOC_Y','SHOT_MADE_FLAG', ...]
    """
    name_to_id = get_name_to_id()
    pid = name_to_id.get(player_name)
    if pid is None:
        st.error(f"No data found for {player_name}")
        return pd.DataFrame()

    resp = shotchartdetail.ShotChartDetail(
        team_id=0,
        player_id=pid,
        season_nullable=season,
        context_measure_simple="FGA"
    )
    league_df = resp.get_data_frames()[1]  # league avgs
    player_df = resp.get_data_frames()[0]  # player shots
    player_df = _attach_venue_and_opponent(player_df) # teams
    return player_df, league_df

# Multi shot log
def load_shotlog_multi(player_name: str, seasons: list[str]):
    """
    Load and concatenate shot logs for a player over multiple seasons.
    Adds a SEASON column to each chunk before concatenating.
    Returns (player_df, league_df).
    """
    frames_p, frames_l = [], []

    for s in seasons:
        p, l = load_shotlog(player_name, s)
        if not p.empty:
            p = p.assign(SEASON=s)
            frames_p.append(p)
        if not l.empty:
            l = l.assign(SEASON=s)
            frames_l.append(l)

    player_df = pd.DataFrame() if not frames_p else pd.concat(frames_p, ignore_index=True)
    league_df = pd.DataFrame() if not frames_l else pd.concat(frames_l, ignore_index=True)

    return player_df, league_df
