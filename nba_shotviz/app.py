"""
Streamlit entry point for the 3D NBA shot visualization app.

- Player and season selection are behind a submit button to avoid repeated API calls.
- Other controls update the visualization using already-loaded shot data.
"""

import streamlit as st

from src.viz_3d import render_3d_trajectories
from src.filters import default_filter_state, filter_df
from src.data_io import (
    get_available_players,
    get_available_seasons,
    load_shotlog,
    load_shotlog_multi,
    get_name_to_id,
)


st.set_page_config(page_title="Player Development — 3D Shot Viz", layout="wide")

st.markdown(
    """
    <style>
    button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# SIDEBAR
st.sidebar.title("Filters")

available_players = get_available_players()
available_seasons = get_available_seasons()

# Session state to hold the last loaded dataset
if "loaded_key" not in st.session_state:
    st.session_state.loaded_key = None
    st.session_state.player_df = None
    st.session_state.league_df = None

    # initialize season range to latest season
    latest_idx = len(available_seasons) - 1
    default_season = available_seasons[latest_idx]
    st.session_state.season_min = default_season
    st.session_state.season_max = default_season

# Form
with st.sidebar.form("dataset_picker"):
    sel_player = st.selectbox("Player", available_players, index=0)

    latest_idx = len(available_seasons) - 1
    default_season = available_seasons[latest_idx]

    season_min = st.selectbox(
        "Season (min)",
        available_seasons,
        index=available_seasons.index(st.session_state.season_min),
    )
    season_max = st.selectbox(
        "Season (max)",
        available_seasons,
        index=available_seasons.index(st.session_state.season_max),
    )

    submitted = st.form_submit_button("Update Visualization")

min_i = available_seasons.index(season_min)
max_i = available_seasons.index(season_max)
if min_i > max_i:
    st.error("Invalid season range: Season (min) must be earlier than Season (max).")
    st.stop()

selected_seasons = available_seasons[min_i : max_i + 1]

st.session_state.season_min = season_min
st.session_state.season_max = season_max

sample = st.sidebar.slider("Max shots to display", 100, 3000, 1000, step=100)

show_heatmap = st.sidebar.checkbox("Show Hot/Cold Zones (vs league)", value=False)
vlim = st.sidebar.slider("Heatmap scale (±FG% points)", 5, 25, 15, step=1) / 100.0

mm = st.sidebar.radio(
    "Result", ["All", "Makes", "Misses"], index=0, horizontal=True
)

rg = st.sidebar.checkbox("Color arcs red/green", value=True)

ha = st.sidebar.radio(
    "Venue", ["All", "Home", "Away"], index=0, horizontal=True
)

# Quarters
st.sidebar.markdown("Quarters")

q1 = st.sidebar.checkbox("Q1", value=True)
q2 = st.sidebar.checkbox("Q2", value=True)
q3 = st.sidebar.checkbox("Q3", value=True)
q4 = st.sidebar.checkbox("Q4", value=True)
ot = st.sidebar.checkbox("OT", value=True)

periods = []
if q1:
    periods.append(1)
if q2:
    periods.append(2)
if q3:
    periods.append(3)
if q4:
    periods.append(4)
if ot:
    periods.append(5)

# Fetch data only when the form is submitted with a new key
requested_key = (sel_player, season_min, season_max)

if submitted and requested_key != st.session_state.loaded_key:
    with st.spinner(f"Loading shot data for {sel_player} — {season_min} to {season_max}…"):
        if len(selected_seasons) > 1:
            player_df, league_df = load_shotlog_multi(sel_player, selected_seasons)
        else:
            player_df, league_df = load_shotlog(sel_player, selected_seasons[0])

        st.session_state.player_df = player_df
        st.session_state.league_df = league_df
        st.session_state.loaded_key = requested_key


tabs = st.tabs(["Visualizer", "About", "Filters", "Project Team"])

if st.session_state.player_df is None:
    with tabs[0]:
        st.title("Interactive NBA Shot Visualization Tool")
        st.info("Pick a player and season(s) on the left, then click **Update Visualization** to see the chart.")
    with tabs[1]:
        st.header("About Player Development — 3D Shot Viz")

        st.markdown(
            """
            ### What this tool is

            **Player Development — 3D Shot Viz** is an interactive web app for exploring NBA shooting patterns
            in a more intuitive way. Instead of just box score stats or 2D charts, you can see each shot as a
            full **3D arc** over a realistic half-court, along with the type of shot, how far it was, and
            whether it went in.

            The app is built with **Streamlit**, the **nba_api** package, and live data from the NBA stats
            API. You choose a player and season range, then use the filters on the left to zero in on specific
            situations.

            Shot data is available all the way back to the 1996–97 season, though older seasons may contain
            occasional inconsistencies due to changes in the NBA’s historical shot-tracking systems.
            """
        )

        st.markdown(
            """
            ### How to use the visualizer

            1. **Pick a player and season range** in the sidebar form, then click **Update Visualization**  
              to load shots for that window.
            2. Use the **filters** below the form to change what shots you are seeing
            3. Hover over any arc to see its **shot type, distance, and result**.
            """
        )

        st.markdown(
            """
            ### Hot/Cold Zone Heatmap (vs League)

            When you toggle **“Show Hot/Cold Zones (vs league)”**, the floor becomes a **heatmap** 
            that compares the selected player's finishing to **league average**:

            - The court is divided into small spatial bins.  
            - For each bin, the player's **field goal percentage** is calculated and compared to 
              the **league FG%** from that bin.
            - We then take the difference: **Player FG% − League FG%**.
            - **Red areas** → the player finishes **better than league average** from that region.  
            - **Blue areas** → the player finishes **worse than league average** there.  
            - Neutral/white → roughly league-average performance.

            In heatmap mode:
            - The arcs can be drawn **in gray** to keep the focus on the zones, or in **green/red** 
              if you enable the color toggle.
            - You are also able to change how sensitive the color scale is using the 
              "Heatmap scale (±FG% points)" filter.
            - The app requires **Result = “All”** to compute the heatmap, because we need 
              both makes *and* misses to estimate FG% fairly.
            """
        )

        st.markdown(
            """
            ### Why we built it

            Traditional shooting charts can be flat and hard to interpret at a glance. By combining:
            - **3D shot trajectories**
            - **Contextual filters** (period, distance, type, opponent, venue)
            - And a **league-relative hot/cold map**

            This tool is designed to help:
            - Players and trainers explore development areas  
            - Analysts and scouts quickly spot spatial strengths and weaknesses  
            - Fans get a deeper, more visual understanding of how and where a player scores

            Our goal is to make advanced shot data feel **visual, interactive, and fun**, 
            without losing the analytical precision under the hood.
            """
        )


    with tabs[2]:
        st.header("Filters")
        st.markdown(
            """
            Use the filters in the left sidebar to customize the visualization:

            **Max shots to display**  
            - Limits how many shots are shown.  
            - If the dataset is larger than the max, a random sample is taken.
            - Helpful for speeding up rendering or looking a smaller sample.

            **Result (All / Makes / Misses)**  
            - **All**: shows every shot in the dataset.  
            - **Makes**: only made shots are included.  
            - **Misses**: only missed shots are included.
            - This must be set to "All" for the heatmap to work.

            **Venue (All / Home / Away)**  
            - Filter shots by where the game was played.  
            - *Home*: games where the selected player's team is listed as the home team.  
            - *Away*: games where they are listed as the road team.

            **Quarters (Q1, Q2, Q3, Q4, OT)**  
            - Toggle which periods to include.  
            - OT includes all overtimes

            **Shot Distance**  
            - Bucketed ranges in feet from the basket (e.g., 0–4 ft, 24–29 ft).
            - Hovering over the shot arc also shows you the exact distance.

            **Shot Type**  
            - Based on the `ACTION_TYPE` from the NBA play data. 
              (e.g., *Jump Shot*, *Layup*, *Driving Dunk*)

            **Opponent**  
            - Filter shots by the opposing team.  
            - Use this to see how a player performs against a specific matchup.

            **Show Hot/Cold Zones (vs league)**  
            - When enabled, overlays a floor heatmap comparing the player's FG% to
              league-average FG% by zone.  
            - **Blue areas**: player is colder than league average.  
            - **Red areas**: player is hotter than league average.  
            - Hovering over the zone shows the player's FG%, the league average, and the difference (Δ).

            **Heatmap scale (±FG% points)**  
            - Controls how “sensitive” the color scale is.  
            - Smaller values highlight subtle differences; larger values emphasize only
              big gaps from league average.

            **Color arcs red/green**  
            - When on, made shots are shown in green and misses in red.  
            - When off, all arcs are rendered in a neutral gray color. 
              (especially useful when a heatmap is displayed underneath)
            - Hovering over a shot arc will always say if it was a make or miss.

            **Clutch shots only** (coming soon)
            - Shows only shots taken in close game situations
            - "The clutch" is defined as the last 2 minutes of the 4th quarter 
              and overtime when the score margin is 5 or less
            """
        )
    with tabs[3]:
        st.header("Project Team")

        st.markdown(
            """
            We’re **Arvind Madan** (Raleigh, NC) and **Daniel Fulk** (Winston–Salem, NC) — two UNC Tar Heels who
            both did our undergrad at **UNC–Chapel Hill** and are now in the **Master of Applied Data Science**
            program at UNC as well. Arvind majored in **Statistics** and **Data Analytics**, and Daniel majored in
            **Economics** with a minor in **Data Science**.

            We first met playing pickup basketball back in 2021, and have been friends since. We both like to 
            play and watch basketball. We are both Tar Heel fans but Daniel's nba team is the Charlotte Hornets and 
            Arvind's is the Miami Heat. Daniel also played for his high school team and now is an assistant coach.

            This project was created for our course **“Visualizations & Communication”** at UNC. It combines two
            things we care a lot about: **sports** and **data analytics**. We’ve both spent our time in school
            building projects around sports analytics (not just basketball), and our long-term goal is to work in
            **sports data analytics** professionally.

            A big inspiration for this app is the work of **Kirk Goldsberry** and his iconic visualizations. Our goal
            wasn’t to build an interactive tool where fans, analysts, and students can explore shot patterns in 3D, 
            experiment with filters, and use features like the **hot/cold zone heatmap** for player insights.

            If you’d like to connect with us:
            - [Arvind on LinkedIn](https://www.linkedin.com/in/arvind-aditya-madan-08271174/)
            - [Daniel on LinkedIn](https://www.linkedin.com/in/daniel-fulk-80a88a240/)
            """
        )


    st.stop()

# At this point, we know data is available in session state
loaded_player, loaded_min, loaded_max = st.session_state.loaded_key
player_df = st.session_state.player_df
league_df = st.session_state.league_df

shot_dist_presets = {
    "All": (0, 100),
    "0–4 ft": (0, 4),
    "5–10 ft": (5, 10),
    "11–16 ft": (11, 16),
    "17–23 ft": (17, 23),
    "24–29 ft": (24, 29),
    "30+ ft": (30, 100),
}
sdist = st.sidebar.selectbox("Shot Distance", list(shot_dist_presets.keys()), index=0)

# Player headshot
pid = get_name_to_id().get(loaded_player)
headshot_url = None
if pid is not None:
    headshot_url = f"https://cdn.nba.com/headshots/nba/latest/260x190/{pid}.png"

# Shot type dropdown
if "ACTION_TYPE" in player_df.columns:
    action_types = ["All"] + sorted(player_df["ACTION_TYPE"].dropna().unique().tolist())
else:
    action_types = ["All"]
stype = st.sidebar.selectbox("Shot Type", action_types, index=0)

# Opponent dropdown
if "OPPONENT" in player_df.columns:
    opponents = ["All"] + sorted(player_df["OPPONENT"].dropna().unique().tolist())
else:
    opponents = ["All"]
opp = st.sidebar.selectbox("Opponent", opponents, index=0)


# Build filter state 
state = default_filter_state()
state["player"]        = loaded_player
state["season"]        = (loaded_min, loaded_max)
state["periods"]       = periods
state["sample"]        = sample
state["result"]        = mm
state["venue"]         = ha
state["opponent"]      = opp
state["shot_distance"] = shot_dist_presets[sdist]
state["action_type"]   = stype

# Heatmap requires all shotss
if show_heatmap and state["result"] != "All":
    st.error(
        "Hot/Cold Zones can only be computed when **Result = 'All'**.\n\n"
        "Switch Result back to **All**, or turn off **Show Hot/Cold Zones**."
    )
    st.stop()

df_filtered = filter_df(player_df, state)


with tabs[0]:
    st.title("Interactive NBA Shot Visualization Tool")
    range_label = loaded_min if loaded_min == loaded_max else f"{loaded_min} — {loaded_max}"
    st.caption(f"{loaded_player} — {range_label}")

    # shot profile summary 

    total_shots = len(df_filtered)
    makes = df_filtered["SHOT_MADE_FLAG"].sum()
    fg_pct = makes / total_shots if total_shots > 0 else 0

    avg_dist = (
        df_filtered["SHOT_DISTANCE"].mean()
        if "SHOT_DISTANCE" in df_filtered.columns
        else None
    )

    colA, colB, colC = st.columns(3)

    colA.metric("Total Shots", f"{total_shots}")
    colB.metric("FG%", f"{fg_pct:.1%}")
    colC.metric("Avg Shot Distance", f"{avg_dist:.1f} ft" if avg_dist else "—")


    col1, col2 = st.columns([0.75, 0.25])
    # Right column: player headshot + team logos
    with col2:
        if headshot_url:
            st.image(headshot_url, width=150)

        # team logos 
        team_ids = sorted(player_df["TEAM_ID"].dropna().unique().tolist())
        logo_urls = [
            f"https://cdn.nba.com/logos/nba/{tid}/global/L/logo.svg"
            for tid in team_ids
        ]

        # Adjust logo size
        if len(logo_urls) <= 1:
            logo_size = 150
        elif len(logo_urls) == 2:
            logo_size = 120
        else:
            logo_size = 90

        st.markdown(
            """
            <div style="display:flex; flex-direction:column; align-items:flex-end; margin-top:10px;">
            """,
            unsafe_allow_html=True,
        )

        for url in logo_urls:
            st.markdown(
                f'<img src="{url}" width="{logo_size}" style="margin:4px 0;" />',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # Left column: main 3D visualization
    with col1:
        if df_filtered.empty:
            st.info("No shots to display. Try different filters.")
        else:
            render_3d_trajectories(
                df_filtered,
                league_df=league_df,
                sample=state["sample"],
                overlay_heatmap=show_heatmap,
                vlim=vlim,
                force_make_miss_colors=rg,
            )


with tabs[1]:
    st.header("About Player Development — 3D Shot Viz")

    st.markdown(
        """
        ### What this tool is

        **Player Development — 3D Shot Viz** is an interactive web app for exploring NBA shooting patterns
        in a more intuitive way. Instead of just box score stats or 2D charts, you can see each shot as a
        full **3D arc** over a realistic half-court, along with the type of shot, how far it was, and
        whether it went in.

        The app is built with **Streamlit**, the **nba_api** package, and live data from the NBA stats
        API. You choose a player and season range, then use the filters on the left to zero in on specific
        situations.

        Shot data is available all the way back to the 1996–97 season, though older seasons may contain
        occasional inconsistencies due to changes in the NBA’s historical shot-tracking systems.
        """
    )

    st.markdown(
        """
        ### How to use the visualizer

        1. **Pick a player and season range** in the sidebar form, then click **Update Visualization**
           to load shots for that window.
        2. Use the **filters** in the sidebar to narrow down context (quarters, venue, distance, etc.).
        3. Hover over any arc to see its **shot type, distance, and result**.
        """
    )

    st.markdown(
        """
        ### Hot/Cold Zone Heatmap (vs league)

        When you toggle **“Show Hot/Cold Zones (vs league)”**, the floor becomes a **heatmap**
        that compares the selected player's finishing to **league average**:

        - The court is divided into small spatial bins.
        - For each bin, the player's **field goal percentage** is calculated and compared to
          the **league FG%** from that bin.
        - We then take the difference: **Player FG% − League FG%**.
        - **Red areas** → the player finishes **better than league average** from that region.
        - **Blue areas** → the player finishes **worse than league average** there.
        - Neutral/white → roughly league-average performance.

        In heatmap mode:
        - The arcs can be drawn **in gray** to keep the focus on the zones, or in **green/red**
          if you enable the color toggle.
        - You can adjust how sensitive the color scale is using the
          "Heatmap scale (±FG% points)" filter.
        - The app requires **Result = “All”** to compute the heatmap, because we need
          both makes *and* misses to estimate FG% fairly.
        """
    )

    st.markdown(
        """
        ### Why we built it

        Traditional shooting charts can be flat and hard to interpret at a glance. By combining:
        - **3D shot trajectories**
        - **Contextual filters** (period, distance, type, opponent, venue)
        - And a **league-relative hot/cold map**

        This tool is designed to help:
        - Players and trainers explore development areas
        - Analysts and scouts quickly spot spatial strengths and weaknesses
        - Fans get a deeper, more visual understanding of how and where a player scores

        Our goal is to make advanced shot data feel **visual, interactive, and fun**,
        without losing the analytical precision under the hood.
        """
    )


with tabs[2]:
    st.header("Filters")

    st.markdown(
        """
        Use the filters in the left sidebar to customize the visualization.

        **Max shots to display**
        - Limits how many shots are shown.
        - If the dataset is larger than the max, a random sample is taken.
        - Helpful for speeding up rendering or focusing on a smaller sample.

        **Result (All / Makes / Misses)**
        - **All**: shows every shot in the dataset.
        - **Makes**: only made shots are included.
        - **Misses**: only missed shots are included.
        - Must be set to "All" for the heatmap to work.

        **Venue (All / Home / Away)**
        - Filter shots by where the game was played.
        - *Home*: games where the selected player's team is listed as the home team.
        - *Away*: games where they are listed as the road team.

        **Quarters (Q1, Q2, Q3, Q4, OT)**
        - Toggle which periods to include.
        - OT includes all overtimes.

        **Shot Distance**
        - Bucketed ranges in feet from the basket (e.g., 0–4 ft, 24–29 ft).
        - Hovering over the shot arc also shows you the exact distance.

        **Shot Type**
        - Based on the `ACTION_TYPE` from the NBA play data
          (e.g., *Jump Shot*, *Layup*, *Driving Dunk*).

        **Opponent**
        - Filter shots by the opposing team.
        - Use this to see how a player performs against specific matchups.

        **Show Hot/Cold Zones (vs league)**
        - Overlays a floor heatmap comparing the player's FG% to league-average FG% by zone.
        - **Blue**: colder than league average.
        - **Red**: hotter than league average.
        - Hovering over a zone shows the player's FG%, the league average, and the difference (Δ).

        **Heatmap scale (±FG% points)**
        - Controls how “sensitive” the color scale is.
        - Smaller values highlight subtle differences; larger values emphasize only big gaps.

        **Color arcs red/green**
        - When on, made shots are shown in green and misses in red.
        - When off, all arcs are drawn in a neutral gray, which can help when a heatmap is shown.

        **Clutch shots only** (coming soon)
        - Will show only shots taken in late-game, close-score situations.
        """
    )

with tabs[3]:
    st.header("Project Team")

    st.markdown(
        """
        We’re **Arvind Madan** (Raleigh, NC) and **Daniel Fulk** (Winston–Salem, NC) — two UNC Tar Heels who
        both did our undergrad at **UNC–Chapel Hill** and are now in the **Master of Applied Data Science**
        program at UNC as well. Arvind majored in **Statistics** and **Data Analytics**, and Daniel majored in
        **Economics** with a minor in **Data Science**.

        We first met playing pickup basketball back in 2021, and have been friends since. We both like to
        play and watch basketball. We are both Tar Heel fans but Daniel's NBA team is the Charlotte Hornets and
        Arvind's is the Miami Heat. Daniel also played for his high school team and now is an assistant coach.

        This project was created for our course **“Visualizations & Communication”** at UNC. It combines two
        things we care a lot about: **sports** and **data analytics**. We’ve both spent our time in school
        building projects around sports analytics (not just basketball), and our long-term goal is to work in
        **sports data analytics** professionally.

        A big inspiration for this app is the work of **Kirk Goldsberry** and his iconic visualizations. Our goal
        is to build an interactive tool where fans, analysts, and students can explore shot patterns in 3D,
        experiment with filters, and use features like the **hot/cold zone heatmap** for player insights.

        If you’d like to connect with us:
        - [Arvind on LinkedIn](https://www.linkedin.com/in/arvind-aditya-madan-08271174/)
        - [Daniel on LinkedIn](https://www.linkedin.com/in/daniel-fulk-80a88a240/)
        """
    )
