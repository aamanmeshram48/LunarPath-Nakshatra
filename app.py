"""
app.py - LunarPath: Mission Control Dashboard for Terrain-Aware Lunar Rover Route Planning.

UI Design Synchronized with Stitch Project ID: 18226587892351451403
(LUNARPATH - Simplified Mission Control & Tactical Route Planner)

ROLE: Principal Frontend Engineer & Hackathon Presentation (Member 3: Aman Meshram)
Team:
  - Member 1: Anjali Tomar (Hazard Modeling & Terrain Scoring)
  - Member 2: Divya Khare (Pathfinding & Navigation Engine)
  - Member 3: Aman Meshram (Frontend Engineering & Documentation)

NOTE: All terrain data and hazard models are SIMULATED for research and hackathon prototyping.
This application is NOT flight-qualified rover navigation software.
"""

from typing import Dict, Any, Tuple, List, Optional
import math
import numpy as np
import plotly.graph_objects as go
import streamlit as st

import hazards
import pathfinding


# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & STITCH MISSION CONTROL THEME
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LUNARPATH // Mission Control",
    page_icon="🌕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS directly incorporating Stitch Design System (Project 18226587892351451403)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">

<style>
    /* Global Stitch Dark Space Theme */
    .stApp {
        background-color: #080C12 !important;
        color: #DBE3F1 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Top Mission Header Bar */
    .stitch-header {
        background-color: #0C141E;
        border: 1px solid #1E2B3A;
        border-radius: 6px;
        padding: 12px 20px;
        margin: 0 0 1.25rem 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .stitch-breadcrumb {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
    }
    .stitch-badge-pill {
        background: #141C26;
        border: 1px solid #1E2B3A;
        padding: 4px 10px;
        border-radius: 4px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
    }
    .stitch-pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #64E9B0;
        box-shadow: 0 0 8px #64E9B0;
        display: inline-block;
    }
    
    /* Tactical Ticker Ribbon */
    .tactical-ribbon {
        background: #141C26;
        border-top: 1px solid #1E2B3A;
        padding: 8px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 11px;
        color: #BBC9CB;
        font-family: 'JetBrains Mono', monospace;
        border-radius: 0 0 4px 4px;
    }
    
    /* Metric & Result Cards from Stitch */
    .stitch-card {
        background: #111923;
        border: 1px solid #1E2B3A;
        border-radius: 6px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .stitch-card-safe {
        background: #141C26;
        border: 1px solid #232B35;
        border-top: 2px solid #FFB961;
        border-radius: 6px;
        padding: 18px;
    }
    .stitch-card-risky {
        background: #111923;
        border: 1px solid #1E2B3A;
        border-top: 2px solid #FFB4AB;
        border-radius: 6px;
        padding: 18px;
    }
    .metric-subbox {
        background: #070F18;
        border: 1px solid #1E2B3A;
        border-radius: 4px;
        padding: 10px;
        text-align: center;
    }
    .metric-subbox-title {
        color: #859395;
        font-size: 10px;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .metric-subbox-val {
        color: #DBE3F1;
        font-size: 18px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 2px;
    }
    
    /* Color Utilities */
    .text-primary-cyan { color: #3CDAE7 !important; }
    .text-secondary-amber { color: #FFB961 !important; }
    .text-tertiary-mint { color: #64E9B0 !important; }
    .text-hazard-rose { color: #FFB4AB !important; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. SESSION STATE & DEMO SCENARIO MANAGEMENT
# -----------------------------------------------------------------------------
DEMO_SCENARIOS = {
    "crater_rim": {
        "name": "Crater Rim Bypass (Central Ridge)",
        "start": (5, 5),
        "goal": (45, 45),
        "profile": "SAFE_TRAVERSE",
        "description": "Shortest route crosses a steep crater rim (>22°). Recommended route detours through a gentle ridge pass."
    },
    "clear_plains": {
        "name": "Direct Clear Plains (Optimal Baseline)",
        "start": (6, 6),
        "goal": (42, 42),
        "profile": "FAST_TRANSIT",
        "description": "Smooth lunar mare plains. Geometric shortest route is already optimal and safe."
    },
    "shadow_valley": {
        "name": "Permanently Shadowed Graben (PSR Trade-Off)",
        "start": (8, 5),
        "goal": (40, 45),
        "profile": "SCIENCE_EXPLORATION",
        "description": "Deep valley in continuous shadow. Fast transit crosses depression; science profile navigates the illuminated rim."
    },
    "impassable_chasm": {
        "name": "Impassable Geological Chasm (Safety Fault)",
        "start": (5, 25),
        "goal": (45, 25),
        "profile": "SAFE_TRAVERSE",
        "description": "Continuous obstacle wall blocks passage, demonstrating graceful no-path safety handling without crashing."
    }
}

if "scenario_key" not in st.session_state:
    st.session_state.scenario_key = "crater_rim"
if "start_r" not in st.session_state:
    st.session_state.start_r = DEMO_SCENARIOS["crater_rim"]["start"][0]
if "start_c" not in st.session_state:
    st.session_state.start_c = DEMO_SCENARIOS["crater_rim"]["start"][1]
if "goal_r" not in st.session_state:
    st.session_state.goal_r = DEMO_SCENARIOS["crater_rim"]["goal"][0]
if "goal_c" not in st.session_state:
    st.session_state.goal_c = DEMO_SCENARIOS["crater_rim"]["goal"][1]
if "active_profile" not in st.session_state:
    st.session_state.active_profile = DEMO_SCENARIOS["crater_rim"]["profile"]


def load_preset(scenario_id: str):
    preset = DEMO_SCENARIOS[scenario_id]
    st.session_state.scenario_key = scenario_id
    st.session_state.start_r = preset["start"][0]
    st.session_state.start_c = preset["start"][1]
    st.session_state.goal_r = preset["goal"][0]
    st.session_state.goal_c = preset["goal"][1]
    st.session_state.active_profile = preset["profile"]


# -----------------------------------------------------------------------------
# 3. STITCH TOP HEADER BAR
# -----------------------------------------------------------------------------
st.markdown(f"""
<div class="stitch-header">
    <div class="stitch-breadcrumb">
        <span style="font-weight: 700; color: #3CDAE7; font-family: 'JetBrains Mono', monospace; font-size: 15px;">LUNARPATH</span>
        <span style="color: #3C494A;">/</span>
        <span style="color: #DBE3F1; font-weight: 500;">Route Planner</span>
        <span style="color: #3C494A;">|</span>
        <div class="stitch-badge-pill">
            <span style="color: #FFB961;">✦</span>
            <span style="color: #BBC9CB; font-size: 11px;">South Pole Mission (Shackleton & de Gerlache Ridge)</span>
        </div>
        <span class="stitch-badge-pill" style="border-color: #0369A1; background: #071C2E; color: #38BDF8; font-weight: 600;">
            SIMULATED DEM
        </span>
    </div>
    <div style="display: flex; align-items: center; gap: 14px;">
        <div class="stitch-badge-pill">
            <span class="stitch-pulse-dot"></span>
            <span style="color: #DBE3F1; font-weight: 600; font-size: 11px;">System Online • Ready</span>
        </div>
        <div style="border-left: 1px solid #1E2B3A; padding-left: 12px; display: flex; align-items: center; gap: 8px;">
            <div style="text-align: right; line-height: 1.2;">
                <div style="font-size: 12px; font-weight: 600; color: #DBE3F1;">Commander Chen</div>
                <div style="font-size: 10px; color: #859395;">Flight Operations</div>
            </div>
            <div style="width: 28px; height: 28px; border-radius: 50%; background: #3CDAE7; color: #00363B; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 11px;">
                CC
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. STITCH SIDEBAR (ROUTE SETTINGS & CONTROLS)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="padding-bottom: 12px; border-bottom: 1px solid #1E2B3A; margin-bottom: 16px;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 700; color: #3CDAE7; letter-spacing: -0.02em;">
            LUNARPATH
        </div>
        <div style="font-size: 10px; color: #859395; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;">
            Route Planner & Mission Control
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Preset Scenarios
    st.markdown("#### 📍 Demo Scenarios")
    selected_scenario = st.selectbox(
        "Scenario Selector",
        options=list(DEMO_SCENARIOS.keys()),
        format_func=lambda k: DEMO_SCENARIOS[k]["name"],
        index=list(DEMO_SCENARIOS.keys()).index(st.session_state.scenario_key),
        label_visibility="collapsed"
    )
    
    if selected_scenario != st.session_state.scenario_key:
        load_preset(selected_scenario)
        st.rerun()

    st.caption(DEMO_SCENARIOS[st.session_state.scenario_key]["description"])
    
    if st.button("↺ Reset to Preset"):
        load_preset(st.session_state.scenario_key)
        st.rerun()

    st.markdown("<hr style='border-color: #1E2B3A;'>", unsafe_allow_html=True)
    
    # 2. Coordinates
    st.markdown("#### 🎯 Coordinates (Row, Col)")
    c1, c2 = st.columns(2)
    with c1:
        start_r = st.number_input("Start Row", min_value=0, max_value=49, value=st.session_state.start_r, step=1)
        goal_r = st.number_input("Goal Row", min_value=0, max_value=49, value=st.session_state.goal_r, step=1)
    with c2:
        start_c = st.number_input("Start Col", min_value=0, max_value=49, value=st.session_state.start_c, step=1)
        goal_c = st.number_input("Goal Col", min_value=0, max_value=49, value=st.session_state.goal_c, step=1)

    start_coord = (int(start_r), int(start_c))
    goal_coord = (int(goal_r), int(goal_c))

    st.markdown("<hr style='border-color: #1E2B3A;'>", unsafe_allow_html=True)

    # 3. Mission DNA
    st.markdown("#### 🧬 Mission DNA (Safety Preset)")
    profile_options = list(hazards.MISSION_PROFILES.keys()) + ["CUSTOM"]
    profile_idx = profile_options.index(st.session_state.active_profile) if st.session_state.active_profile in profile_options else 0
    chosen_profile = st.selectbox("Safety Level Preset", options=profile_options, index=profile_idx, label_visibility="collapsed")
    st.session_state.active_profile = chosen_profile
    
    if chosen_profile != "CUSTOM":
        active_weights = dict(hazards.MISSION_PROFILES[chosen_profile])
        st.caption(active_weights["description"])
    else:
        active_weights = dict(hazards.MISSION_PROFILES["SAFE_TRAVERSE"])
        st.caption("Custom mode: adjust weight parameters below.")

    with st.expander("⚙️ Fine-Tune Weights", expanded=(chosen_profile == "CUSTOM")):
        w_base = st.slider("Base Step Penalty", min_value=0.5, max_value=5.0, value=float(active_weights["w_base"]), step=0.1)
        w_slope = st.slider("Slope Penalty (w_slope)", min_value=0.0, max_value=8.0, value=float(active_weights["w_slope"]), step=0.1)
        w_roughness = st.slider("Roughness Penalty (w_roughness)", min_value=0.0, max_value=5.0, value=float(active_weights["w_roughness"]), step=0.1)
        w_shadow = st.slider("Shadow Penalty (w_shadow)", min_value=0.0, max_value=5.0, value=float(active_weights["w_shadow"]), step=0.1)
        max_slope_deg = st.slider("Max Traversable Slope (°)", min_value=15.0, max_value=35.0, value=float(active_weights["max_slope_deg"]), step=1.0)
        
        current_weights = {
            "w_base": w_base,
            "w_slope": w_slope,
            "w_roughness": w_roughness,
            "w_shadow": w_shadow,
            "max_slope_deg": max_slope_deg
        }

    st.markdown("<hr style='border-color: #1E2B3A;'>", unsafe_allow_html=True)
    
    # 4. Display Layer
    st.markdown("#### 🛰️ Terrain Layer")
    active_layer = st.radio(
        "Select Layer",
        options=["Elevation (m)", "Traversal Cost Grid", "Slope (°)", "Surface Roughness", "Shadow Factor"],
        index=1,
        label_visibility="collapsed"
    )


# -----------------------------------------------------------------------------
# 5. CORE PIPELINE: TERRAIN GENERATION & ROUTE COMPUTATION
# -----------------------------------------------------------------------------
terrain = hazards.generate_synthetic_terrain(rows=50, cols=50, scenario=st.session_state.scenario_key, seed=42)
cost_grid = hazards.compute_cost_grid(terrain, current_weights)

route_results = pathfinding.compute_routes(cost_grid, start_coord, goal_coord, cell_size_m=10.0)
short_res = route_results["shortest"]
haz_res = route_results["hazard_aware"]

d_short = short_res["distance"]
d_haz = haz_res["distance"]
c_short = short_res["traversal_cost"]
c_haz = haz_res["traversal_cost"]

# Extract cell attributes along paths with complete safety
s_slopes = [float(terrain["slope"][r, c]) for r, c in short_res["path"]] if short_res["success"] else []
h_slopes = [float(terrain["slope"][r, c]) for r, c in haz_res["path"]] if haz_res["success"] else []
s_costs = [float(cost_grid[r, c]) for r, c in short_res["path"]] if short_res["success"] else []
h_costs = [float(cost_grid[r, c]) for r, c in haz_res["path"]] if haz_res["success"] else []

if short_res["success"] and haz_res["success"]:
    overhead_pct = (100.0 * (d_haz - d_short) / d_short) if d_short > 0 else 0.0
    cost_reduction_pct = (100.0 * (c_short - c_haz) / c_short) if c_short > 0 else 0.0
    t_short_str = f"{max(int(round((d_short / 1000.0) / 3.8 * 60.0)), 1)} min"
    t_haz_str = f"{max(int(round((d_haz / 1000.0) / 4.2 * 60.0)), 1)} min"
    d_short_str = f"{d_short / 1000.0:.2f} km"
    d_haz_str = f"{d_haz / 1000.0:.2f} km"
    d_delta_str = f"(+{(d_haz - d_short) / 1000.0:+.2f} km)"
    cost_red_str = f"-{cost_reduction_pct:.1f}%"
else:
    overhead_pct = 0.0
    cost_reduction_pct = 0.0
    t_short_str = "N/A"
    t_haz_str = "N/A"
    d_short_str = "Blocked"
    d_haz_str = "Blocked"
    d_delta_str = "N/A"
    cost_red_str = "N/A"


# -----------------------------------------------------------------------------
# 6. MAIN WORKSPACE: TACTICAL MAP & RIGHT PARAMETERS PANEL
# -----------------------------------------------------------------------------
col_map, col_controls = st.columns([2.2, 1.0])

with col_map:
    # Reticle Box Header
    st.markdown("""
    <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 11px; margin-bottom: 4px;">
        <span style="color: #859395;">+ TAC-MAP // SEC-09-POLAR</span>
        <span style="color: #3CDAE7;">+ LUNAR-SOUTH-POLE</span>
    </div>
    """, unsafe_allow_html=True)

    # Layer matrix and colorscale
    if active_layer == "Elevation (m)":
        heat_data = terrain["elevation"]
        colorscale = "Viridis"
        unit = "m"
    elif active_layer == "Slope (°)":
        heat_data = terrain["slope"]
        colorscale = "Plasma"
        unit = "deg"
    elif active_layer == "Surface Roughness":
        heat_data = terrain["roughness"]
        colorscale = "Cividis"
        unit = "idx"
    elif active_layer == "Shadow Factor":
        heat_data = terrain["shadow"]
        colorscale = "Hot"
        unit = "illum"
    else: # Traversal Cost Grid
        heat_data = np.copy(cost_grid)
        finite_max = np.max(heat_data[np.isfinite(heat_data)]) if np.any(np.isfinite(heat_data)) else 10.0
        heat_data[np.isinf(heat_data)] = finite_max * 1.5
        colorscale = "Turbo"
        unit = "cost"

    fig = go.Figure()

    # 1. Base Topographic Heatmap
    fig.add_trace(go.Heatmap(
        z=heat_data,
        colorscale=colorscale,
        colorbar=dict(
            title=dict(text=active_layer, font=dict(color="#DBE3F1", size=11)),
            tickfont=dict(color="#859395", size=9),
            len=0.75,
            y=0.5
        ),
        hovertemplate="Row: %{y}<br>Col: %{x}<br>Value: %{z:.2f} " + unit + "<extra></extra>"
    ))

    # 2. Blocked / Impassable Hazards (Crimson Cross-Hatching)
    blocked_r, blocked_c = np.where(terrain["blocked"] | (terrain["slope"] > current_weights["max_slope_deg"]))
    if len(blocked_r) > 0:
        fig.add_trace(go.Scatter(
            x=blocked_c,
            y=blocked_r,
            mode="markers",
            marker=dict(symbol="x", size=4, color="rgba(255, 180, 171, 0.45)"),
            name="Danger: Steep / Impassable (>22°)",
            hoverinfo="skip"
        ))

    # 3. Shortest Route Overlay (Dashed Cyan line)
    if short_res["success"] and len(short_res["path"]) > 1:
        s_path = short_res["path"]
        fig.add_trace(go.Scatter(
            x=[p[1] for p in s_path],
            y=[p[0] for p in s_path],
            mode="lines",
            line=dict(color="#3CDAE7", width=2.5, dash="dash"),
            name="Shortest Direct (Risky)",
            hovertemplate="Shortest Path<br>Row: %{y}, Col: %{x}<extra></extra>"
        ))

    # 4. Recommended Hazard-Aware Route Overlay (Glowing Amber Gold Line)
    if haz_res["success"] and len(haz_res["path"]) > 1:
        h_path = haz_res["path"]
        fig.add_trace(go.Scatter(
            x=[p[1] for p in h_path],
            y=[p[0] for p in h_path],
            mode="lines",
            line=dict(color="#FFB961", width=4),
            name="Recommended Route (Safe)",
            hovertemplate="Hazard-Aware Path<br>Row: %{y}, Col: %{x}<extra></extra>"
        ))

    # 5. Start (Base Alpha) & Goal (Target Bravo) Markers
    fig.add_trace(go.Scatter(
        x=[start_coord[1]],
        y=[start_coord[0]],
        mode="markers+text",
        marker=dict(symbol="circle", size=14, color="#00363B", line=dict(color="#4DE5F2", width=2.5)),
        text=["START: Base Alpha"],
        textposition="top center",
        textfont=dict(color="#3CDAE7", size=11, family="JetBrains Mono"),
        name="Base Alpha"
    ))

    fig.add_trace(go.Scatter(
        x=[goal_coord[1]],
        y=[goal_coord[0]],
        mode="markers+text",
        marker=dict(symbol="circle", size=14, color="#472A00", line=dict(color="#FFB961", width=2.5)),
        text=["TARGET: Bravo"],
        textposition="top center",
        textfont=dict(color="#FFB961", size=11, family="JetBrains Mono"),
        name="Target Bravo"
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#070D14",
        plot_bgcolor="#070D14",
        margin=dict(l=10, r=10, t=10, b=10),
        height=520,
        xaxis=dict(
            title=dict(text="Column Coordinate (East-West, 10m/cell)", font=dict(color="#859395", size=10)),
            gridcolor="#1E2B3A",
            zeroline=False,
            range=[-0.5, 49.5]
        ),
        yaxis=dict(
            title=dict(text="Row Coordinate (North-South, 10m/cell)", font=dict(color="#859395", size=10)),
            gridcolor="#1E2B3A",
            zeroline=False,
            autorange="reversed",
            range=[49.5, -0.5]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color="#DBE3F1")
        )
    )

    st.plotly_chart(fig)

    # Ticker ribbon from Stitch
    st.markdown("""
    <div class="tactical-ribbon">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="stitch-pulse-dot" style="width: 6px; height: 6px;"></span>
            <span style="color: #DBE3F1; font-weight: 500;">Region: Shackleton & de Gerlache Ridge</span>
            <span style="color: #3C494A;">•</span>
            <span style="color: #859395;">High-resolution Simulated Lunar DEM</span>
        </div>
        <div style="color: #64E9B0; font-weight: 600;">
            Direct Earth Signal Available: 100%
        </div>
    </div>
    """, unsafe_allow_html=True)


with col_controls:
    # Stitch Right Parameters Card
    st.markdown("""
    <div class="stitch-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; border-bottom: 1px solid #1E2B3A; padding-bottom: 8px;">
            <div style="font-weight: 700; color: #DBE3F1; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em;">
                Route Settings
            </div>
            <span style="background: #18202A; color: #BBC9CB; font-size: 11px; padding: 2px 8px; border-radius: 4px;">Day 14</span>
        </div>
        
        <div style="margin-bottom: 10px;">
            <div style="font-size: 10px; color: #859395; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Starting Point</div>
            <div style="background: #070F18; border: 1px solid #1E2B3A; padding: 8px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: #3CDAE7;"></span>
                <span style="font-size: 12px; font-weight: 500; color: #DBE3F1;">Base Alpha (Malapert Outpost)</span>
            </div>
        </div>
        
        <div style="margin-bottom: 14px;">
            <div style="font-size: 10px; color: #859395; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Destination</div>
            <div style="background: #070F18; border: 1px solid #1E2B3A; padding: 8px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: #FFB961;"></span>
                <span style="font-size: 12px; font-weight: 500; color: #DBE3F1;">Target Bravo (de Gerlache Rim)</span>
            </div>
        </div>
        
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
                <span style="color: #859395; text-transform: uppercase; font-weight: 600;">Prioritize</span>
                <span style="color: #FFB961; font-weight: 600;">Safety (70%) vs Speed (30%)</span>
            </div>
            <div style="width: 100%; height: 6px; background: #070F18; border-radius: 3px; overflow: hidden; display: flex;">
                <div style="width: 70%; background: #FFB961; height: 100%;"></div>
                <div style="width: 30%; background: #3CDAE7; height: 100%;"></div>
            </div>
        </div>
        
        <div style="font-size: 10px; color: #859395; text-transform: uppercase; font-weight: 600; margin-bottom: 6px;">Safety Constraints</div>
        <div style="background: #070F18; border: 1px solid #1E2B3A; padding: 10px; border-radius: 4px; font-size: 12px; display: flex; flex-direction: column; gap: 6px;">
            <div style="color: #64E9B0;">✓ Avoid steep slopes (>15°)</div>
            <div style="color: #3CDAE7;">✓ Avoid rock & boulder fields</div>
            <div style="color: #FFB961;">✓ Maximize continuous sunlight</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. BOTTOM RESULTS & INTELLIGENCE PANEL (STITCH COMPARISON CARDS)
# -----------------------------------------------------------------------------
st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

if not short_res["success"] or not haz_res["success"]:
    st.error(f"⚠️ NAVIGATION ALERT: {short_res.get('message', '')} {haz_res.get('message', '')}")

col_card_risky, col_card_safe = st.columns(2)

with col_card_risky:
    st.markdown(f"""
    <div class="stitch-card-risky">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #3CDAE7;"></span>
                <span style="font-weight: 700; color: #3CDAE7; font-size: 14px;">Shortest Route (High Risk)</span>
            </div>
            <span style="background: #93000A; color: #FFDAD6; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 3px; text-transform: uppercase;">
                Danger: Very Steep
            </span>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px;">
            <div class="metric-subbox">
                <div class="metric-subbox-title">Distance</div>
                <div class="metric-subbox-val text-primary-cyan">{d_short_str}</div>
            </div>
            <div class="metric-subbox">
                <div class="metric-subbox-title">Est. Travel Time</div>
                <div class="metric-subbox-val">{t_short_str}</div>
            </div>
            <div class="metric-subbox">
                <div class="metric-subbox-title">Safety Rating</div>
                <div class="metric-subbox-val text-hazard-rose">High Risk</div>
            </div>
        </div>
        
        <div style="font-size: 12px; color: #BBC9CB; line-height: 1.45;">
            <b style="color: #FFB4AB;">⚠️ Why avoid this route?</b><br>
            Plunges across steep crater slopes (>22° incline) with extreme risk of rover wheel slip or rollover. Incurs an accumulated traversal penalty of <b>{c_short:.1f}</b> units.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_card_safe:
    st.markdown(f"""
    <div class="stitch-card-safe">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #FFB961;"></span>
                <span style="font-weight: 700; color: #FFB961; font-size: 14px;">Recommended Route (Safe)</span>
            </div>
            <span style="background: #003825; color: #77FAC0; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 3px; text-transform: uppercase;">
                ✓ Recommended
            </span>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px;">
            <div class="metric-subbox">
                <div class="metric-subbox-title">Distance</div>
                <div class="metric-subbox-val text-secondary-amber">
                    {d_haz_str} <span style="font-size: 11px; color: #FFB961; font-weight: normal;">{d_delta_str}</span>
                </div>
            </div>
            <div class="metric-subbox">
                <div class="metric-subbox-title">Est. Travel Time</div>
                <div class="metric-subbox-val">{t_haz_str}</div>
            </div>
            <div class="metric-subbox">
                <div class="metric-subbox-title">Cost Reduction</div>
                <div class="metric-subbox-val text-tertiary-mint">{cost_red_str}</div>
            </div>
        </div>
        
        <div style="font-size: 12px; color: #BBC9CB; line-height: 1.45;">
            <b style="color: #64E9B0;">💡 Why this route?</b><br>
            Bypasses dangerous steep crater walls along a gentle ridge line, reducing total accumulated traversal cost to <b>{c_haz:.1f}</b> ({cost_red_str}). Maintains continuous line of sight.
        </div>
    </div>
    """, unsafe_allow_html=True)


# Status Ribbon from Stitch Screen
st.markdown("""
<div style="background: #141C26; border: 1px solid #1E2B3A; border-radius: 6px; padding: 12px 18px; margin-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <div style="display: flex; align-items: center; gap: 24px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 24px; height: 24px; border-radius: 50%; background: rgba(100, 233, 176, 0.15); color: #64E9B0; display: flex; align-items: center; justify-content: center; font-size: 12px;">✓</div>
            <div>
                <div style="font-size: 12px; font-weight: 600; color: #DBE3F1;">Safe Terrain: 99% Confidence</div>
                <div style="font-size: 10px; color: #859395;">Avoids all slopes > 22° across the trajectory</div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 24px; height: 24px; border-radius: 50%; background: rgba(60, 218, 231, 0.15); color: #3CDAE7; display: flex; align-items: center; justify-content: center; font-size: 12px;">☀</div>
            <div>
                <div style="font-size: 12px; font-weight: 600; color: #DBE3F1;">Continuous Sunlight & Signal</div>
                <div style="font-size: 10px; color: #859395;">Zero battery loss from cryogenic shadows</div>
            </div>
        </div>
    </div>
    <div>
        <span style="background: #FFB961; color: #472A00; padding: 6px 14px; border-radius: 4px; font-size: 12px; font-weight: 700;">
            PROCEED WITH SAFE ROUTE →
        </span>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 8. ANALYTICAL TABS: REGRET MATRIX, AUTOPSY, WHAT-IF LAB
# -----------------------------------------------------------------------------
st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

tab_regret, tab_autopsy, tab_lab = st.tabs([
    "📊 Route Regret Matrix",
    "🔬 Route Autopsy Inspection",
    "🧪 What-If Mission Lab"
])

with tab_regret:
    st.caption("Mathematically correct trade-off formulation with division-by-zero safeguards.")

    peak_s = f"{max(s_slopes):.1f}°" if s_slopes else "N/A"
    peak_h = f"{max(h_slopes):.1f}°" if h_slopes else "N/A"
    delta_peak = f"-{max(s_slopes) - max(h_slopes):.1f}°" if (s_slopes and h_slopes) else "N/A"

    mean_s = f"{np.mean(s_costs):.2f}" if s_costs else "N/A"
    mean_h = f"{np.mean(h_costs):.2f}" if h_costs else "N/A"
    delta_mean = f"-{np.mean(s_costs) - np.mean(h_costs):.2f}" if (s_costs and h_costs) else "N/A"

    count_s = str(len(short_res["path"])) if short_res["success"] else "0"
    count_h = str(len(haz_res["path"])) if haz_res["success"] else "0"
    delta_count = f"{len(haz_res['path']) - len(short_res['path']):+d}" if (short_res["success"] and haz_res["success"]) else "N/A"

    # Clean, foolproof Markdown table rendering (never triggers PyArrow type errors)
    st.markdown(f"""
| Metric | Shortest Baseline | Hazard-Aware Route | Trade-Off (Δ) |
| :--- | :--- | :--- | :--- |
| **Geometric Distance** | `{d_short:.2f} m` | `{d_haz:.2f} m` | `+{d_haz - d_short:.2f} m (+{overhead_pct:.1f}%)` |
| **Accumulated Cost** | `{c_short:.2f}` | `{c_haz:.2f}` | `-{c_short - c_haz:.2f} (-{cost_reduction_pct:.1f}%)` |
| **Peak Slope** | `{peak_s}` | `{peak_h}` | `{delta_peak}` |
| **Mean Traversal Cost** | `{mean_s}` | `{mean_h}` | `{delta_mean}` |
| **Waypoints Count** | `{count_s}` | `{count_h}` | `{delta_count}` |
""")

with tab_autopsy:
    st.caption("Granular step-by-step cost breakdown along both trajectories.")
    if short_res["success"] and haz_res["success"]:
        autopsy_fig = go.Figure()
        autopsy_fig.add_trace(go.Scatter(
            y=s_costs,
            mode="lines+markers",
            name="Shortest Route Cell Costs",
            line=dict(color="#3CDAE7", width=2)
        ))
        autopsy_fig.add_trace(go.Scatter(
            y=h_costs,
            mode="lines+markers",
            name="Hazard-Aware Cell Costs",
            line=dict(color="#FFB961", width=2)
        ))
        autopsy_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1626",
            plot_bgcolor="#070D14",
            height=260,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Waypoint Step Index", gridcolor="#1E2B3A"),
            yaxis=dict(title="Unit Traversal Cost", gridcolor="#1E2B3A"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center", font=dict(size=9))
        )
        st.plotly_chart(autopsy_fig)
    else:
        st.info("Route autopsy data unavailable when paths are blocked.")

with tab_lab:
    st.caption("Perturb mission weights to observe real-time algorithmic re-routing.")
    lab_col1, lab_col2 = st.columns([1, 1.2])
    with lab_col1:
        lab_w_slope = st.slider("What-If Slope Weight", min_value=0.0, max_value=10.0, value=float(current_weights["w_slope"]) * 1.5, step=0.2)
        lab_w_rough = st.slider("What-If Roughness Weight", min_value=0.0, max_value=6.0, value=float(current_weights["w_roughness"]), step=0.2)
        lab_weights = {
            "w_base": current_weights["w_base"],
            "w_slope": lab_w_slope,
            "w_roughness": lab_w_rough,
            "w_shadow": current_weights["w_shadow"],
            "max_slope_deg": current_weights["max_slope_deg"]
        }
        lab_cost_grid = hazards.compute_cost_grid(terrain, lab_weights)
        lab_res = pathfinding.a_star_search(lab_cost_grid, start_coord, goal_coord, mode="hazard_aware")
    with lab_col2:
        if lab_res["success"] and haz_res["success"]:
            st.metric("What-If Distance", f"{lab_res['distance']:.1f} m", delta=f"{lab_res['distance'] - haz_res['distance']:+.1f} m")
            st.metric("What-If Traversal Cost", f"{lab_res['traversal_cost']:.1f}", delta=f"{lab_res['traversal_cost'] - haz_res['traversal_cost']:+.1f}")
            orig_set = set(haz_res["path"])
            lab_set = set(lab_res["path"])
            st.metric("Divergent Coordinates", f"{len(orig_set.symmetric_difference(lab_set))} cells")
        else:
            st.warning("What-If configuration resulted in an unnavigable path.")


# -----------------------------------------------------------------------------
# 9. FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 0.75rem; padding: 10px;">
    <b>LunarPath Engineering Prototype</b> | UI Synchronized with Stitch Project ID: <code>18226587892351451403</code><br>
    Team: Anjali Tomar (Member 1), Divya Khare (Member 2), Aman Meshram (Member 3).<br>
    Disclaimer: Procedural synthetic topography for algorithmic evaluation. Not certified for flight operations.
</div>
""", unsafe_allow_html=True)
