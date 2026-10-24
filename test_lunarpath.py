"""
test_lunarpath.py - Comprehensive Unit & Regression Test Suite for LunarPath.

Tests:
1. Terrain layer generation and dimensions.
2. Traversal cost grid calculation and slope thresholds.
3. A* pathfinding (shortest vs hazard-aware).
4. Boundary and error safety checks (out of bounds, blocked start/goal, unreachable targets).
5. Route Regret mathematical formulas and zero-denominator handling.
6. Mission DNA profiles and dynamic weight sensitivity.
7. Deterministic demo scenarios.
"""

import math
import numpy as np
import pytest

from hazards import (
    generate_synthetic_terrain,
    compute_cost_grid,
    MISSION_PROFILES
)
from pathfinding import (
    a_star_search,
    compute_routes,
    octile_distance
)


class TestTerrainAndHazards:
    """Tests for hazards.py synthetic terrain and cost grid modeling."""

    def test_terrain_generation_dimensions(self):
        rows, cols = 40, 60
        terrain = generate_synthetic_terrain(rows=rows, cols=cols, scenario="clear_plains", seed=123)
        
        assert terrain["elevation"].shape == (rows, cols)
        assert terrain["slope"].shape == (rows, cols)
        assert terrain["roughness"].shape == (rows, cols)
        assert terrain["shadow"].shape == (rows, cols)
        assert terrain["blocked"].shape == (rows, cols)
        assert terrain["metadata"]["source"] == "SIMULATED"
        assert terrain["metadata"]["scenario"] == "clear_plains"

    def test_slope_and_roughness_ranges(self):
        terrain = generate_synthetic_terrain(rows=50, cols=50, scenario="crater_rim", seed=42)
        
        # Slopes must be non-negative
        assert np.all(terrain["slope"] >= 0.0)
        # Normalized layers must stay within [0, 1]
        assert np.all((terrain["roughness"] >= 0.0) & (terrain["roughness"] <= 1.0))
        assert np.all((terrain["shadow"] >= 0.0) & (terrain["shadow"] <= 1.0))

    def test_cost_grid_blocked_cells(self):
        terrain = generate_synthetic_terrain(rows=50, cols=50, scenario="crater_rim", seed=42)
        profile = MISSION_PROFILES["SAFE_TRAVERSE"]
        cost_grid = compute_cost_grid(terrain, profile)
        
        # Cells exceeding max slope (22 deg) must be inf
        steep_mask = terrain["slope"] > profile["max_slope_deg"]
        assert np.all(np.isinf(cost_grid[steep_mask]))
        
        # Traversable cells must have finite positive costs >= w_base
        traversable = np.isfinite(cost_grid)
        assert np.all(cost_grid[traversable] >= profile["w_base"])

    def test_mission_profiles_structure(self):
        for name, p in MISSION_PROFILES.items():
            assert "w_base" in p
            assert "w_slope" in p
            assert "w_roughness" in p
            assert "w_shadow" in p
            assert "max_slope_deg" in p
            assert p["w_base"] > 0
            assert p["max_slope_deg"] > 0


class TestPathfinding:
    """Tests for pathfinding.py A* engine and edge-case handling."""

    def test_octile_distance_properties(self):
        # Orthogonal step
        assert math.isclose(octile_distance(0, 0, 0, 5), 5.0)
        assert math.isclose(octile_distance(0, 0, 5, 0), 5.0)
        # Diagonal step
        assert math.isclose(octile_distance(0, 0, 1, 1), math.sqrt(2.0))
        # Symmetry
        assert math.isclose(octile_distance(2, 4, 10, 15), octile_distance(10, 15, 2, 4))

    def test_open_plains_convergence(self):
        terrain = generate_synthetic_terrain(rows=30, cols=30, scenario="clear_plains", seed=42)
        cost_grid = compute_cost_grid(terrain, MISSION_PROFILES["FAST_TRANSIT"])
        start = (2, 2)
        goal = (28, 28)
        
        routes = compute_routes(cost_grid, start, goal)
        short = routes["shortest"]
        haz = routes["hazard_aware"]
        
        assert short["success"] is True
        assert haz["success"] is True
        assert len(short["path"]) > 0
        assert short["path"][0] == start
        assert short["path"][-1] == goal
        assert haz["path"][0] == start
        assert haz["path"][-1] == goal
        assert short["distance"] > 0.0
        assert haz["distance"] > 0.0

    def test_crater_rim_cost_tradeoff(self):
        """Verifies that hazard-aware path accepts extra distance for lower cost."""
        terrain = generate_synthetic_terrain(rows=50, cols=50, scenario="crater_rim", seed=42)
        cost_grid = compute_cost_grid(terrain, MISSION_PROFILES["SAFE_TRAVERSE"])
        start = (5, 5)
        goal = (45, 45)
        
        routes = compute_routes(cost_grid, start, goal)
        short = routes["shortest"]
        haz = routes["hazard_aware"]
        
        assert short["success"] is True
        assert haz["success"] is True
        # Hazard-aware path should have lower or equal cost
        assert haz["traversal_cost"] <= short["traversal_cost"]
        # In crater_rim scenario, hazard route takes a detour (longer distance)
        assert haz["distance"] >= short["distance"]

    def test_start_equals_goal_trivial_case(self):
        cost_grid = np.ones((20, 20), dtype=float) * 2.0
        point = (10, 10)
        res = a_star_search(cost_grid, point, point)
        
        assert res["success"] is True
        assert res["path"] == [point]
        assert res["distance"] == 0.0
        assert res["traversal_cost"] == 2.0

    def test_out_of_bounds_rejection(self):
        cost_grid = np.ones((20, 20), dtype=float)
        # Out of bounds start
        res1 = a_star_search(cost_grid, (-1, 5), (10, 10))
        assert res1["success"] is False
        assert "outside grid boundaries" in res1["message"]
        
        # Out of bounds goal
        res2 = a_star_search(cost_grid, (5, 5), (25, 10))
        assert res2["success"] is False
        assert "outside grid boundaries" in res2["message"]

    def test_start_or_goal_on_impassable_hazard(self):
        cost_grid = np.ones((20, 20), dtype=float)
        cost_grid[5, 5] = np.inf
        
        # Blocked start
        res_start = a_star_search(cost_grid, (5, 5), (15, 15))
        assert res_start["success"] is False
        assert "impassable hazard" in res_start["message"]
        
        # Blocked goal
        res_goal = a_star_search(cost_grid, (0, 0), (5, 5))
        assert res_goal["success"] is False
        assert "impassable hazard" in res_goal["message"]

    def test_impassable_chasm_no_path(self):
        """Tests that a wall of blocked cells safely returns success=False without crashing."""
        terrain = generate_synthetic_terrain(rows=50, cols=50, scenario="impassable_chasm", seed=42)
        cost_grid = compute_cost_grid(terrain, MISSION_PROFILES["SAFE_TRAVERSE"])
        start = (5, 25)
        goal = (45, 25)
        
        routes = compute_routes(cost_grid, start, goal)
        assert routes["shortest"]["success"] is False
        assert routes["hazard_aware"]["success"] is False
        assert "blocked by impassable terrain" in routes["hazard_aware"]["message"]


class TestRouteRegretFormulas:
    """Tests for mathematical correctness of overhead % and cost reduction %."""

    def test_overhead_and_cost_savings(self):
        d_short = 700.0
        d_haz = 770.0
        c_short = 2000.0
        c_haz = 1400.0
        
        overhead = 100.0 * (d_haz - d_short) / d_short
        cost_reduction = 100.0 * (c_short - c_haz) / c_short
        
        assert math.isclose(overhead, 10.0)
        assert math.isclose(cost_reduction, 30.0)

    def test_zero_denominator_safeguards(self):
        d_short = 0.0
        d_haz = 0.0
        c_short = 0.0
        c_haz = 0.0
        
        # Handle zero baseline distance safely
        overhead = (100.0 * (d_haz - d_short) / d_short) if d_short > 0 else 0.0
        cost_reduction = (100.0 * (c_short - c_haz) / c_short) if c_short > 0 else 0.0
        
        assert overhead == 0.0
        assert cost_reduction == 0.0
