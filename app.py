"""
app.py - LunarPath: Mission Control Dashboard for Terrain-Aware Lunar Rover Route Planning.

ROLE: Principal Frontend Engineer & Hackathon Final Presentation (Member 3: Aman Meshram)
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
# 1. PAGE CONFIGURATION & CUSTOM MISSION CONTROL THEME
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LunarPath — Mission Control Telemetry",
    page_icon="🌕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for deep-space lunar telemetry aesthetics
st.markdown("""
<style>
    /* Dark space theme base */
    .stApp {
        background-color: #080C14;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Mission Bar */
    .mission-header {
        background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .mission-title {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #F8FAFC;
        margin: 0;
    }
    .badge-simulated {
        background-color: #0369A1;
        color: #E0F2FE;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        padding: 4px 10px;
        border-radius: 4px;
        border: 1px solid #38BDF8;
        display: inline-block;
    }
    .badge-disclaimer {
        color: #94A3B8;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    
    /* Telemetry Hero Metric Cards */
    .telemetry-card {
        background: #111927;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    }
    .metric-label {
        color: #94A3B8;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #F8FAFC;
        font-size: 1.6rem;
        font-weight: 700;
        font-family: "SF Mono", "Consolas", monospace;
    }
    .metric-cyan {
        color: #00F0FF;
    }
    .metric-amber {
        color: #F59E0B;
    }
    .metric-emerald {
        color: #10B981;
    }
    .metric-rose {
        color: #F43F5E;
    }
    
    /* Section containers */
    .section-card {
        background: #0E1626;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .section-title {
        color: #38BDF8;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 12px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. SESSION STATE MANAGEMENT & DEMO SCENARIO INITIALIZATION
# -----------------------------------------------------------------------------
DEMO_SCENARIOS = {
    "crater_rim": {
        "name": "Crater Rim Bypass (Central Ridge)",
        "start": (5, 5),
        "goal": (45, 45),
        "profile": "SAFE_TRAVERSE",
        "description": "Shortest route crosses a steep, rocky crater rim. Hazard-aware route detours through a low-slope pass."
    },
    "clear_plains": {
        "name": "Direct Clear Plains (Optimal Baseline)",
        "start": (6, 6),
        "goal": (42, 42),
        "profile": "FAST_TRANSIT",
        "description": "Smooth lunar mare plains. Geometric shortest route is already cost-optimal and safe."
    },
    "shadow_valley": {
        "name": "Permanently Shadowed Graben (PSR Trade-Off)",
        "start": (8, 5),
        "goal": (40, 45),
        "profile": "SCIENCE_EXPLORATION",
        "description": "Deep linear valley in continuous shadow. Fast transit cuts through; science profile navigates the illuminated rim."
    },
    "impassable_chasm": {
        "name": "Impassable Geological Chasm (Safety Fault)",
        "start": (5, 25),
        "goal": (45, 25),
        "profile": "SAFE_TRAVERSE",
        "description": "Continuous obstacle wall blocks traversal, verifying graceful no-path safety handling without crashing."
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
# 3. TOP MISSION BAR
# -----------------------------------------------------------------------------
st.markdown(f"""
<div class="mission-header">
    <div>
        <h1 class="mission-title">🌕 LUNARPATH // MISSION CONTROL TELEMETRY</h1>
        <div class="badge-disclaimer">
            RESEARCH PROTOTYPE — Algorithmic feasibility demonstration. Not flight-qualified rover navigation software.
        </div>
    </div>
    <div style="text-align: right;">
        <span class="badge-simulated">DATA: SIMULATED (PROCEDURAL DEM)</span>
        <div style="color: #38BDF8; font-size: 0.8rem; font-weight: 600; margin-top: 4px;">
            MISSION PROFILE: {st.session_state.active_profile}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. MISSION SETUP SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ MISSION SETUP")
    
    # Differentiator 5: Live Demo Scenarios
    st.markdown("#### 1. Demo Scenarios")
    selected_scenario = st.selectbox(
        "Select Deterministic Scenario",
        options=list(DEMO_SCENARIOS.keys()),
        format_func=lambda k: DEMO_SCENARIOS[k]["name"],
        index=list(DEMO_SCENARIOS.keys()).index(st.session_state.scenario_key),
        key="scenario_select"
    )
    
    if selected_scenario != st.session_state.scenario_key:
        load_preset(selected_scenario)
        st.rerun()

    st.info(DEMO_SCENARIOS[st.session_state.scenario_key]["description"])
    
    col_reset, col_space = st.columns([1, 1])
    with col_reset:
        if st.button("↺ Reset to Preset"):
            load_preset(st.session_state.scenario_key)
            st.rerun()

    st.markdown("---")
    
    # Coordinate Inputs
    st.markdown("#### 2. Coordinates (Row, Column)")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        start_r = st.number_input("Start Row", min_value=0, max_value=49, value=st.session_state.start_r, step=1)
    with col_s2:
        start_c = st.number_input("Start Col", min_value=0, max_value=49, value=st.session_state.start_c, step=1)
        
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        goal_r = st.number_input("Goal Row", min_value=0, max_value=49, value=st.session_state.goal_r, step=1)
    with col_g2:
        goal_c = st.number_input("Goal Col", min_value=0, max_value=49, value=st.session_state.goal_c, step=1)

    start_coord = (int(start_r), int(start_c))
    goal_coord = (int(goal_r), int(goal_c))

    st.markdown("---")
    
    # Differentiator 1: Mission DNA (Profile Selector & Weights)
    st.markdown("#### 3. Mission DNA (Profile)")
    profile_options = list(hazards.MISSION_PROFILES.keys()) + ["CUSTOM"]
    profile_idx = profile_options.index(st.session_state.active_profile) if st.session_state.active_profile in profile_options else 0
    chosen_profile = st.selectbox("Mission DNA Preset", options=profile_options, index=profile_idx)
    st.session_state.active_profile = chosen_profile
    
    if chosen_profile != "CUSTOM":
        active_weights = dict(hazards.MISSION_PROFILES[chosen_profile])
        st.caption(active_weights["description"])
    else:
        active_weights = dict(hazards.MISSION_PROFILES["SAFE_TRAVERSE"])
        st.caption("Custom mission weighting: manually adjust individual penalties.")

    # Configurable Weights
    with st.expander("⚙️ View / Adjust Weights", expanded=(chosen_profile == "CUSTOM")):
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

    st.markdown("---")
    
    # Layer Display Toggle
    st.markdown("#### 4. Display Layer")
    active_layer = st.radio(
        "Heatmap Layer",
        options=["Elevation (m)", "Traversal Cost Grid", "Slope (°)", "Surface Roughness", "Shadow Factor"],
        index=1
    )


# -----------------------------------------------------------------------------
# 5. CORE PIPELINE: TERRAIN GENERATION & ROUTE COMPUTATION
# -----------------------------------------------------------------------------
# Generate synthetic terrain deterministically for the selected scenario
terrain = hazards.generate_synthetic_terrain(rows=50, cols=50, scenario=st.session_state.scenario_key, seed=42)
cost_grid = hazards.compute_cost_grid(terrain, current_weights)

# Calculate both Shortest and Hazard-Aware routes
route_results = pathfinding.compute_routes(cost_grid, start_coord, goal_coord, cell_size_m=10.0)
short_res = route_results["shortest"]
haz_res = route_results["hazard_aware"]


# -----------------------------------------------------------------------------
# 6. HERO METRIC STRIP & MATHEMATICAL VALIDATION
# -----------------------------------------------------------------------------
# Handle division-by-zero safely for overhead and cost reduction
d_short = short_res["distance"]
d_haz = haz_res["distance"]
c_short = short_res["traversal_cost"]
c_haz = haz_res["traversal_cost"]

if short_res["success"] and haz_res["success"]:
    overhead_pct = (100.0 * (d_haz - d_short) / d_short) if d_short > 0 else 0.0
    cost_reduction_pct = (100.0 * (c_short - c_haz) / c_short) if c_short > 0 else 0.0
else:
    overhead_pct = 0.0
    cost_reduction_pct = 0.0

m1, m2, m3, m4, m5, m6 = st.columns(6)

with m1:
    st.markdown(f"""
    <div class="telemetry-card">
        <div class="metric-label">Shortest Distance</div>
        <div class="metric-value metric-amber">{d_short:.1f} m</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="telemetry-card">
        <div class="metric-label">Hazard-Aware Dist</div>
        <div class="metric-value metric-cyan">{d_haz:.1f} m</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="telemetry-card">
        <div class="metric-label">Shortest Cost</div>
        <div class="metric-value metric-amber">{c_short:.1f}</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="telemetry-card">
        <div class="metric-label">Hazard-Aware Cost</div>
        <div class="metric-value metric-cyan">{c_haz:.1f}</div>
    </div>
    """, unsafe_allow_html=True)

with m5:
    ov_color = "metric-rose" if overhead_pct > 20 else ("metric-amber" if overhead_pct > 0 else "metric-emerald")
    st.markdown(f"""
    <div class="telemetry-card">
        <div class="metric-label">Distance Overhead</div>
        <div class="metric-value {ov_color}">+{overhead_pct:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with m6:
    cr_color = "metric-emerald" if cost_reduction_pct > 0 else "metric-amber"
    st.markdown(f"""
    <div class="telemetry-card">
        <div class="metric-label">Cost Reduction</div>
        <div class="metric-value {cr_color}">-{cost_reduction_pct:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. MAIN TERRAIN EXPLORER (PLOTLY 2D HEATMAP)
# -----------------------------------------------------------------------------
col_map, col_analysis = st.columns([1.6, 1.0])

with col_map:
    st.markdown("#### 🗺️ MAIN TERRAIN EXPLORER")
    
    # Select layer matrix and colorscale
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
        # Cap inf values for clean visual display, marking blocked cells clearly
        heat_data = np.copy(cost_grid)
        finite_max = np.max(heat_data[np.isfinite(heat_data)]) if np.any(np.isfinite(heat_data)) else 10.0
        heat_data[np.isinf(heat_data)] = finite_max * 1.5
        colorscale = "Turbo"
        unit = "cost"

    # Construct Plotly Figure
    fig = go.Figure()

    # 1. Base Terrain Heatmap
    fig.add_trace(go.Heatmap(
        z=heat_data,
        colorscale=colorscale,
        colorbar=dict(title=dict(text=active_layer, font=dict(color="#E2E8F0")), tickfont=dict(color="#94A3B8")),
        hovertemplate="Row: %{y}<br>Col: %{x}<br>Value: %{z:.2f} " + unit + "<extra></extra>"
    ))

    # 2. Blocked Obstacle Indicator (cross-hatching / scatter for blocked cells)
    blocked_r, blocked_c = np.where(terrain["blocked"] | (terrain["slope"] > current_weights["max_slope_deg"]))
    if len(blocked_r) > 0:
        fig.add_trace(go.Scatter(
            x=blocked_c,
            y=blocked_r,
            mode="markers",
            marker=dict(symbol="x", size=4, color="rgba(239, 68, 68, 0.4)"),
            name="Impassable / Blocked",
            hoverinfo="skip"
        ))

    # 3. Route Overlays
    if short_res["success"] and len(short_res["path"]) > 1:
        s_path = short_res["path"]
        fig.add_trace(go.Scatter(
            x=[p[1] for p in s_path],
            y=[p[0] for p in s_path],
            mode="lines",
            line=dict(color="#F59E0B", width=3, dash="dot"),
            name="Shortest Route (Min Distance)",
            hovertemplate="Shortest Path<br>Row: %{y}, Col: %{x}<extra></extra>"
        ))

    if haz_res["success"] and len(haz_res["path"]) > 1:
        h_path = haz_res["path"]
        fig.add_trace(go.Scatter(
            x=[p[1] for p in h_path],
            y=[p[0] for p in h_path],
            mode="lines",
            line=dict(color="#00F0FF", width=4),
            name="Hazard-Aware Route (Min Cost)",
            hovertemplate="Hazard-Aware Path<br>Row: %{y}, Col: %{x}<extra></extra>"
        ))

    # 4. Start & Goal Markers
    fig.add_trace(go.Scatter(
        x=[start_coord[1]],
        y=[start_coord[0]],
        mode="markers+text",
        marker=dict(symbol="circle", size=14, color="#10B981", line=dict(color="#FFFFFF", width=2)),
        text=["START"],
        textposition="top center",
        textfont=dict(color="#10B981", size=11, family="monospace"),
        name="Rover Origin"
    ))

    fig.add_trace(go.Scatter(
        x=[goal_coord[1]],
        y=[goal_coord[0]],
        mode="markers+text",
        marker=dict(symbol="star", size=16, color="#00F0FF", line=dict(color="#FFFFFF", width=2)),
        text=["GOAL"],
        textposition="top center",
        textfont=dict(color="#00F0FF", size=11, family="monospace"),
        name="Target Site"
    ))

    # Layout styling for aerospace dark mode
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1626",
        plot_bgcolor="#080C14",
        margin=dict(l=20, r=20, t=30, b=20),
        height=540,
        xaxis=dict(
            title="Column Coordinate (East-West, 10m/cell)",
            gridcolor="#1E293B",
            zeroline=False,
            range=[-0.5, 49.5]
        ),
        yaxis=dict(
            title="Row Coordinate (North-South, 10m/cell)",
            gridcolor="#1E293B",
            zeroline=False,
            autorange="reversed", # Standard image / matrix indexing
            range=[49.5, -0.5]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color="#E2E8F0")
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Route status messages
    if not short_res["success"] or not haz_res["success"]:
        st.error(f"⚠️ NAVIGATION FAULT: {short_res.get('message', '')} {haz_res.get('message', '')}")
    else:
        st.success(f"✓ {haz_res['message']} | Nodes explored: Shortest={short_res['nodes_explored']}, Hazard-Aware={haz_res['nodes_explored']}")


# -----------------------------------------------------------------------------
# 8. ROUTE COMPARISON & MISSION EXPLANATION PANEL
# -----------------------------------------------------------------------------
with col_analysis:
    st.markdown("#### ⚖️ ROUTE TRADE-OFF ANALYSIS")
    
    with st.container():
        st.markdown(f"""
        <div class="section-card">
            <div class="section-title">Telemetry Trade-Off Summary</div>
            <p style="font-size: 0.9rem; color: #CBD5E1; line-height: 1.5;">
                The <b>Hazard-Aware Route</b> accepts 
                <span style="color: #38BDF8; font-weight: 700;">+{d_haz - d_short:.1f} m</span> 
                (+{overhead_pct:.1f}%) of physical detour in exchange for reducing total accumulated traversal cost by 
                <span style="color: #10B981; font-weight: 700;">{c_short - c_haz:.1f}</span> 
                (-{cost_reduction_pct:.1f}%).
            </p>
            <hr style="border-color: #1E293B;">
            <div style="font-size: 0.82rem; color: #94A3B8;">
                <b>Recommendation Rationale:</b> Under the <code>{st.session_state.active_profile}</code> profile, 
                minimizing the quadratic slope penalty reduces chassis pitch rates, regolith slippage, and actuator strain.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Mission Explanation Panel (deterministic findings from actual data)
    st.markdown("#### 🔍 DETERMINISTIC MISSION EXPLANATION")
    
    if short_res["success"] and haz_res["success"]:
        # Extract actual cell characteristics traversed by both paths
        s_slopes = [float(terrain["slope"][r, c]) for r, c in short_res["path"]]
        h_slopes = [float(terrain["slope"][r, c]) for r, c in haz_res["path"]]
        
        s_costs = [float(cost_grid[r, c]) for r, c in short_res["path"]]
        h_costs = [float(cost_grid[r, c]) for r, c in haz_res["path"]]

        max_s_slope = max(s_slopes) if s_slopes else 0.0
        max_h_slope = max(h_slopes) if h_slopes else 0.0
        max_s_cost = max(s_costs) if s_costs else 0.0
        max_h_cost = max(h_costs) if h_costs else 0.0

        st.markdown(f"""
        * **Peak Slope Encountered**:
          * Shortest Route: **{max_s_slope:.1f}°**
          * Hazard-Aware Route: **{max_h_slope:.1f}°** ({max_s_slope - max_h_slope:+.1f}° reduction)
        * **Peak Cell Traversal Cost**:
          * Shortest Route: **{max_s_cost:.2f}**
          * Hazard-Aware Route: **{max_h_cost:.2f}**
        * **Active Weights Applied**:
          * Slope: `{current_weights['w_slope']}`, Roughness: `{current_weights['w_roughness']}`, Shadow: `{current_weights['w_shadow']}`
        """)
    else:
        st.warning("Routes could not be fully evaluated due to an impassable barrier.")


# -----------------------------------------------------------------------------
# 9. DIFFERENTIATOR 2 & 3: ROUTE REGRET & ROUTE AUTOPSY
# -----------------------------------------------------------------------------
st.markdown("---")
col_regret, col_autopsy = st.columns([1, 1])

with col_regret:
    st.markdown("### 📊 DIFFERENTIATOR: ROUTE REGRET MATRIX")
    st.caption("Mathematically correct trade-off formulation with division-by-zero safeguards.")

    regret_data = [
        {
            "Metric": "Geometric Distance",
            "Shortest Baseline": f"{d_short:.2f} m",
            "Hazard-Aware Route": f"{d_haz:.2f} m",
            "Trade-Off (Δ)": f"+{d_haz - d_short:.2f} m (+{overhead_pct:.1f}%)"
        },
        {
            "Metric": "Accumulated Cost",
            "Shortest Baseline": f"{c_short:.2f}",
            "Hazard-Aware Route": f"{c_haz:.2f}",
            "Trade-Off (Δ)": f"-{c_short - c_haz:.2f} (-{cost_reduction_pct:.1f}%)"
        },
        {
            "Metric": "Peak Slope",
            "Shortest Baseline": f"{max(s_slopes):.1f}°" if (short_res['success'] and s_slopes) else "N/A",
            "Hazard-Aware Route": f"{max(h_slopes):.1f}°" if (haz_res['success'] and h_slopes) else "N/A",
            "Trade-Off (Δ)": f"-{max(s_slopes) - max(h_slopes):.1f}°" if (short_res['success'] and s_slopes) else "N/A"
        },
        {
            "Metric": "Mean Traversal Cost",
            "Shortest Baseline": f"{np.mean(s_costs):.2f}" if (short_res['success'] and s_costs) else "N/A",
            "Hazard-Aware Route": f"{np.mean(h_costs):.2f}" if (haz_res['success'] and h_costs) else "N/A",
            "Trade-Off (Δ)": f"-{np.mean(s_costs) - np.mean(h_costs):.2f}" if (short_res['success'] and s_costs) else "N/A"
        },
        {
            "Metric": "Waypoints Count",
            "Shortest Baseline": len(short_res["path"]),
            "Hazard-Aware Route": len(haz_res["path"]),
            "Trade-Off (Δ)": f"{len(haz_res['path']) - len(short_res['path']):+d}"
        }
    ]
    st.table(regret_data)

with col_autopsy:
    st.markdown("### 🔬 DIFFERENTIATOR: ROUTE AUTOPSY")
    st.caption("Granular step-by-step cost breakdown along both trajectories.")

    if short_res["success"] and haz_res["success"]:
        # Distribution of cost along trajectory steps
        autopsy_fig = go.Figure()
        autopsy_fig.add_trace(go.Scatter(
            y=s_costs,
            mode="lines+markers",
            name="Shortest Route Cell Costs",
            line=dict(color="#F59E0B", width=2)
        ))
        autopsy_fig.add_trace(go.Scatter(
            y=h_costs,
            mode="lines+markers",
            name="Hazard-Aware Cell Costs",
            line=dict(color="#00F0FF", width=2)
        ))
        autopsy_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1626",
            plot_bgcolor="#080C14",
            height=260,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Waypoint Step Index", gridcolor="#1E293B"),
            yaxis=dict(title="Unit Traversal Cost", gridcolor="#1E293B"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center", font=dict(size=9))
        )
        st.plotly_chart(autopsy_fig, use_container_width=True)
    else:
        st.info("Route autopsy data unavailable when paths are blocked.")


# -----------------------------------------------------------------------------
# 10. DIFFERENTIATOR 4: WHAT-IF MISSION LAB
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🧪 DIFFERENTIATOR: WHAT-IF MISSION LAB")
st.caption("Perturb mission weights to observe real-time algorithmic re-routing and waypoint divergence.")

with st.expander("Launch What-If Mission Lab Controls", expanded=False):
    lab_col1, lab_col2, lab_col3 = st.columns([1, 1, 1.2])
    
    with lab_col1:
        st.markdown("**Perturb Mission Weights**")
        lab_w_slope = st.slider("What-If Slope Weight", min_value=0.0, max_value=10.0, value=float(current_weights["w_slope"]) * 1.5, step=0.2)
        lab_w_rough = st.slider("What-If Roughness Weight", min_value=0.0, max_value=6.0, value=float(current_weights["w_roughness"]), step=0.2)
        lab_w_shadow = st.slider("What-If Shadow Weight", min_value=0.0, max_value=6.0, value=float(current_weights["w_shadow"]), step=0.2)
        lab_max_slope = st.slider("What-If Max Slope (°)", min_value=15.0, max_value=35.0, value=float(current_weights["max_slope_deg"]), step=1.0)
        
    lab_weights = {
        "w_base": current_weights["w_base"],
        "w_slope": lab_w_slope,
        "w_roughness": lab_w_rough,
        "w_shadow": lab_w_shadow,
        "max_slope_deg": lab_max_slope
    }
    
    lab_cost_grid = hazards.compute_cost_grid(terrain, lab_weights)
    lab_res = pathfinding.a_star_search(lab_cost_grid, start_coord, goal_coord, mode="hazard_aware")
    
    with lab_col2:
        st.markdown("**Simulation Comparison**")
        if lab_res["success"] and haz_res["success"]:
            # Check coordinate divergence
            orig_set = set(haz_res["path"])
            lab_set = set(lab_res["path"])
            divergent_coords = orig_set.symmetric_difference(lab_set)
            
            st.metric("What-If Route Distance", f"{lab_res['distance']:.1f} m", delta=f"{lab_res['distance'] - haz_res['distance']:+.1f} m")
            st.metric("What-If Traversal Cost", f"{lab_res['traversal_cost']:.1f}", delta=f"{lab_res['traversal_cost'] - haz_res['traversal_cost']:+.1f}")
            st.metric("Divergent Waypoints", f"{len(divergent_coords)} cells")
        else:
            st.warning("What-If configuration resulted in an unnavigable path.")

    with lab_col3:
        st.markdown("**Trajectory Delta Plot**")
        if lab_res["success"] and haz_res["success"]:
            lab_fig = go.Figure()
            lab_fig.add_trace(go.Scatter(
                x=[p[1] for p in haz_res["path"]],
                y=[p[0] for p in haz_res["path"]],
                mode="lines",
                name="Original Hazard Route",
                line=dict(color="#00F0FF", width=3)
            ))
            lab_fig.add_trace(go.Scatter(
                x=[p[1] for p in lab_res["path"]],
                y=[p[0] for p in lab_res["path"]],
                mode="lines",
                name="What-If Route",
                line=dict(color="#EC4899", width=3, dash="dash")
            ))
            lab_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0E1626",
                plot_bgcolor="#080C14",
                height=260,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(autorange=True, gridcolor="#1E293B"),
                yaxis=dict(autorange="reversed", gridcolor="#1E293B"),
                legend=dict(font=dict(size=9))
            )
            st.plotly_chart(lab_fig, use_container_width=True)


# -----------------------------------------------------------------------------
# 11. SCIENTIFIC HONESTY FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 0.75rem; padding: 10px;">
    <b>LunarPath Engineering Prototype</b> | Developed for the Nakshatra AI Vibe-Coding Hackathon | 
    Team: Anjali Tomar (Member 1), Divya Khare (Member 2), Aman Meshram (Member 3).<br>
    Disclaimer: Procedural synthetic topography for algorithmic evaluation. Not certified for flight operations.
</div>
""", unsafe_allow_html=True)
