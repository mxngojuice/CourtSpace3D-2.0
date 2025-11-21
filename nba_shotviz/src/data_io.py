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


# 1) Single cached raw list of dictionaries for each player
@st.cache_data(show_spinner=False)
def get_active_players_raw():
    # Returns list[dict] with keys like 'id', 'full_name'
    return players.get_active_players()

# 2) Cached name list for UI
@st.cache_data(show_spinner=False)
def get_available_players():
    return sorted([p["full_name"] for p in get_active_players_raw()])

# 3) Cached name -> id map for instant lookups
@st.cache_data(show_spinner=False)
def get_name_to_id():
    return {p["full_name"]: p["id"] for p in get_active_players_raw()}

# 4) Seasons (unchanged; tweak start/end as you like)
@st.cache_data(show_spinner=False)
def get_available_seasons(start: int = 2010, end: int = 2025):
    # Produces strings like '2016-17'
    return [f"{y}-{str(y+1)[-2:]}" for y in range(start, end)]

# mxngo) Teams
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

# 5) Shot log loader: use the cached map (O(1) lookup)
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
    player_df = _attach_venue_and_opponent(player_df) # teams mxngo
    return player_df, league_df

# mxngo
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

# %%writefile src/data_io.py
# """
# Data access helpers for Streamlit app:
# - Active players (cached)
# - Seasons list (cached)
# - Shot log loader via nba_api (cached)
# """

# import pandas as pd
# import streamlit as st
# from nba_api.stats.static import players, teams
# from nba_api.stats.endpoints import shotchartdetail, playbyplayv2


# # 1) Single cached raw list of dictionaries for each player
# @st.cache_data(show_spinner=False)
# def get_active_players_raw():
#     # Returns list[dict] with keys like 'id', 'full_name'
#     return players.get_active_players()


# # 2) Cached name list for UI
# @st.cache_data(show_spinner=False)
# def get_available_players():
#     return sorted([p["full_name"] for p in get_active_players_raw()])


# # 3) Cached name -> id map for instant lookups
# @st.cache_data(show_spinner=False)
# def get_name_to_id():
#     return {p["full_name"]: p["id"] for p in get_active_players_raw()}


# # 4) Seasons (unchanged; tweak start/end as you like)
# @st.cache_data(show_spinner=False)
# def get_available_seasons(start: int = 2010, end: int = 2025):
#     # Produces strings like '2016-17'
#     return [f"{y}-{str(y+1)[-2:]}" for y in range(start, end)]


# # mxngo) Teams
# @st.cache_data(show_spinner=False)
# def get_team_maps():
#     tlst = teams.get_teams()
#     id2abbr  = {t["id"]: t["abbreviation"] for t in tlst}
#     abbr2full= {t["abbreviation"]: t["full_name"] for t in tlst}
#     id2full  = {t["id"]: t["full_name"] for t in tlst}
#     return id2abbr, abbr2full, id2full


# def _attach_venue_and_opponent(player_df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Adds:
#       - TEAM_ABBR
#       - VENUE: "Home"/"Away"/"Unknown"
#       - OPPONENT_ABBR
#       - OPPONENT (full name)
#     Uses HTM/VTM from ShotChartDetail.
#     """
#     if player_df.empty:
#         return player_df

#     id2abbr, abbr2full, _ = get_team_maps()

#     df = player_df.copy()
#     df["TEAM_ABBR"] = df["TEAM_ID"].map(id2abbr)

#     # Venue
#     venue = pd.Series("Unknown", index=df.index)
#     venue = venue.mask(df["TEAM_ABBR"].eq(df["HTM"]), "Home")
#     venue = venue.mask(df["TEAM_ABBR"].eq(df["VTM"]), "Away")
#     df["VENUE"] = venue

#     # Opponent (abbr + full)
#     opp_abbr = pd.Series(pd.NA, index=df.index)
#     opp_abbr = opp_abbr.mask(df["VENUE"].eq("Home"), df["VTM"])
#     opp_abbr = opp_abbr.mask(df["VENUE"].eq("Away"), df["HTM"])
#     df["OPPONENT_ABBR"] = opp_abbr
#     df["OPPONENT"] = df["OPPONENT_ABBR"].map(abbr2full)

#     return df



# @st.cache_data(show_spinner=False)
# def _get_pbp_for_games(game_ids: tuple[str, ...]) -> pd.DataFrame:
#     """
#     Fetch play-by-play for each GAME_ID and return a combined DataFrame
#     with columns:
#       - GAME_ID
#       - EVENTNUM
#       - SCOREMARGIN (home-team perspective)
#     We keep it small on purpose.
#     """
#     if not game_ids:
#         return pd.DataFrame()

#     frames = []
#     for gid in game_ids:
#         try:
#             pbp = playbyplayv2.PlayByPlayV2(game_id=gid).get_data_frames()[0]
#         except Exception as e:
#             # If something fails for a game, just skip it
#             st.warning(f"Failed to fetch PBP for game {gid}: {e}")
#             continue

#         # Keep only what's needed
#         keep_cols = ["EVENTNUM", "SCOREMARGIN"]
#         # Some older seasons may not have SCOREMARGIN; guard for that
#         for col in keep_cols:
#             if col not in pbp.columns:
#                 pbp[col] = pd.NA

#         pbp = pbp[keep_cols].copy()
#         pbp["GAME_ID"] = gid
#         frames.append(pbp)

#     if not frames:
#         return pd.DataFrame()

#     return pd.concat(frames, ignore_index=True)


# def _attach_clutch_flag(
#     player_df: pd.DataFrame,
#     margin_threshold: int = 5,
#     time_threshold: float = 5.0,
# ) -> pd.DataFrame:
#     """
#     Add a score-aware CLUTCH flag to player_df.

#     Definition:
#       - 4th quarter or later (PERIOD >= 4)
#       - Time remaining in the period <= time_threshold (minutes)
#       - Absolute score margin for *shooting team* <= margin_threshold

#     Implementation details:
#       - SCOREMARGIN from PBP is home-team perspective.
#       - We flip the sign if the player is the away team, using VENUE.
#     """
#     if player_df.empty:
#         return player_df

#     df = player_df.copy()

#     # Need PBP joined on GAME_ID + GAME_EVENT_ID <-> EVENTNUM
#     if "GAME_ID" not in df.columns or "GAME_EVENT_ID" not in df.columns:
#         # If these don't exist for some weird reason, just set False
#         df["CLUTCH"] = False
#         return df

#     # Pull PBP for all games in this DF
#     game_ids = tuple(df["GAME_ID"].dropna().unique().tolist())
#     pbp = _get_pbp_for_games(game_ids)

#     if pbp.empty:
#         df["CLUTCH"] = False
#         return df

#     # Clean SCOREMARGIN into numeric (home perspective)
#     # SCOREMARGIN values can be like "3", "-2", "TIE", or NaN
#     pbp["SCOREMARGIN_NUM"] = (
#         pbp["SCOREMARGIN"]
#         .replace({"TIE": 0})
#         .pipe(pd.to_numeric, errors="coerce")
#         .fillna(0)
#         .astype(int)
#     )

#     # Merge shots with PBP by GAME_ID + event id
#     merged = df.merge(
#         pbp[["GAME_ID", "EVENTNUM", "SCOREMARGIN_NUM"]],
#         left_on=["GAME_ID", "GAME_EVENT_ID"],
#         right_on=["GAME_ID", "EVENTNUM"],
#         how="left",
#     )

#     # team margin: from the shooter's point of view
#     # SCOREMARGIN_NUM is home - away.
#     # If player is away, flip sign.
#     # If VENUE is unknown or missing, treat as home-perspective.
#     home_mask = merged["VENUE"].eq("Home")
#     away_mask = merged["VENUE"].eq("Away")

#     team_margin = merged["SCOREMARGIN_NUM"].copy()
#     team_margin = team_margin.where(home_mask | ~away_mask, -team_margin)
#     merged["TEAM_MARGIN"] = team_margin

#     # Time remaining in minutes
#     merged["TIME_REMAINING_MIN"] = (
#         merged["MINUTES_REMAINING"] + merged["SECONDS_REMAINING"] / 60.0
#     )

#     merged["CLUTCH"] = (
#         (merged["PERIOD"] >= 4)
#         & (merged["TIME_REMAINING_MIN"] <= time_threshold)
#         & (merged["TEAM_MARGIN"].abs() <= margin_threshold)
#     )

#     # We don't need EVENTNUM in final DF; drop to avoid duplicates on re-use
#     if "EVENTNUM" in merged.columns:
#         merged = merged.drop(columns=["EVENTNUM"])

#     return merged


# # 5) Shot log loader: use the cached map (O(1) lookup)
# @st.cache_data(show_spinner=True)
# def load_shotlog(player_name: str, season: str):
#     """
#     Returns (player_df, league_df) where player_df has at least:
#       ['LOC_X','LOC_Y','SHOT_MADE_FLAG', ... 'VENUE','OPPONENT','CLUTCH']
#     """
#     name_to_id = get_name_to_id()
#     pid = name_to_id.get(player_name)
#     if pid is None:
#         st.error(f"No data found for {player_name}")
#         return pd.DataFrame(), pd.DataFrame()

#     resp = shotchartdetail.ShotChartDetail(
#         team_id=0,
#         player_id=pid,
#         season_nullable=season,
#         context_measure_simple="FGA",
#     )
#     league_df = resp.get_data_frames()[1]  # league avgs
#     player_df = resp.get_data_frames()[0]  # player shots

#     # Attach team/venue/opponent info
#     player_df = _attach_venue_and_opponent(player_df)
#     # Attach score-aware clutch flag
#     player_df = _attach_clutch_flag(player_df)

#     return player_df, league_df


# def load_shotlog_multi(player_name: str, seasons: list[str]):
#     """
#     Load and concatenate shot logs for a player over multiple seasons.
#     Adds a SEASON column to each chunk before concatenating.
#     Returns (player_df, league_df).

#     player_df includes VENUE, OPPONENT, CLUTCH.
#     """
#     frames_p, frames_l = [], []

#     for s in seasons:
#         p, l = load_shotlog(player_name, s)
#         if not p.empty:
#             p = p.assign(SEASON=s)
#             frames_p.append(p)
#         if not l.empty:
#             l = l.assign(SEASON=s)
#             frames_l.append(l)

#     player_df = pd.DataFrame() if not frames_p else pd.concat(frames_p, ignore_index=True)
#     league_df = pd.DataFrame() if not frames_l else pd.concat(frames_l, ignore_index=True)

#     return player_df, league_df


