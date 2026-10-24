"""
hazards.py - Terrain Traversal Cost Modeling for Lunar Rover Route Planning.

NOTE: All terrain data and hazard models in this module are SIMULATED for research
and prototyping purposes. This module does NOT represent flight-qualified lunar
navigation software and should not be used for actual spaceflight operations.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np


# Mission profile preset weights
MISSION_PROFILES: Dict[str, Dict[str, float]] = {
    "SAFE_TRAVERSE": {
        "w_base": 1.0,
        "w_slope": 3.5,
        "w_roughness": 2.5,
        "w_shadow": 0.5,
        "max_slope_deg": 22.0,
        "description": "Prioritizes mechanical safety and vehicle stability by heavily penalizing steep slopes and rough boulder fields."
    },
    "FAST_TRANSIT": {
        "w_base": 2.0,
        "w_slope": 1.0,
        "w_roughness": 0.8,
        "w_shadow": 0.2,
        "max_slope_deg": 26.0,
        "description": "Emphasizes transit speed and direct distance, accepting moderate terrain gradients within mechanical limits."
    },
    "SCIENCE_EXPLORATION": {
        "w_base": 1.0,
        "w_slope": 1.8,
        "w_roughness": 1.5,
        "w_shadow": 3.0,
        "max_slope_deg": 24.0,
        "description": "Maintains solar power and thermal stability by steering clear of deep shadows, or targeting illuminated ridges."
    }
}


def generate_synthetic_terrain(
    rows: int = 50,
    cols: int = 50,
    scenario: str = "crater_rim",
    seed: int = 42
) -> Dict[str, Any]:
    """
    Generates synthetic lunar terrain layers using deterministic procedural methods.
    
    All outputs are explicitly marked as SIMULATED.
    
    Parameters:
        rows: Grid height (number of rows).
        cols: Grid width (number of columns).
        scenario: Preset scenario ('crater_rim', 'clear_plains', 'shadow_valley', 'impassable_chasm').
        seed: Random seed for reproducibility.
        
    Returns:
        Dictionary containing:
            - elevation: 2D np.ndarray (meters)
            - slope: 2D np.ndarray (degrees, 0-90)
            - roughness: 2D np.ndarray (normalized index 0.0-1.0)
            - shadow: 2D np.ndarray (normalized shadow factor 0.0=sunlit, 1.0=deep shadow)
            - blocked: 2D np.ndarray of bool (unnavigable cells)
            - metadata: Provenance and parameter dictionary
    """
    rng = np.random.RandomState(seed)
    
    # Base procedural elevation using multi-frequency components
    x = np.linspace(-3.0, 3.0, cols)
    y = np.linspace(-3.0, 3.0, rows)
    xx, yy = np.meshgrid(x, y)
    
    # Smooth baseline undulating topography
    elevation = (
        15.0 * np.sin(0.8 * xx) * np.cos(0.8 * yy)
        + 8.0 * np.cos(1.5 * xx + 0.5 * yy)
        + rng.normal(0, 0.4, (rows, cols))
    )
    
    roughness = np.clip(
        0.15 + 0.1 * np.abs(np.sin(xx * 2.0)) + rng.uniform(0.0, 0.15, (rows, cols)),
        0.0, 1.0
    )
    
    # Base low-angle illumination model (sun azimuth ~45 deg, low elevation)
    shadow = np.clip(
        0.2 + 0.3 * np.sin(xx + yy) + rng.uniform(0.0, 0.1, (rows, cols)),
        0.0, 1.0
    )
    
    blocked = np.zeros((rows, cols), dtype=bool)
    
    if scenario == "crater_rim":
        # Introduce a prominent crater feature in the central corridor (rows 18-32, cols 15-35)
        crater_center = (25.0, 25.0)
        dist_from_center = np.sqrt((xx - (crater_center[1] - cols/2)/(cols/6))**2 + 
                                  (yy - (crater_center[0] - rows/2)/(rows/6))**2)
        
        # Inverted Gaussian depression with a raised rim
        crater_mask = np.exp(-1.8 * (dist_from_center - 1.2)**2)
        depression = -35.0 * np.exp(-2.5 * dist_from_center**2)
        rim = 28.0 * crater_mask
        elevation += depression + rim
        
        # Roughness spikes on crater ejecta blanket and rim
        roughness += 0.55 * crater_mask
        roughness = np.clip(roughness, 0.0, 1.0)
        
        # Deep cast shadow inside the western interior rim
        interior_shadow = np.where((dist_from_center < 1.1) & (xx < 0.2), 0.85, 0.0)
        shadow = np.clip(shadow + interior_shadow, 0.0, 1.0)
        
        # Impassable boulder blocks on the most extreme rim fractures
        extreme_rim = (dist_from_center > 1.0) & (dist_from_center < 1.35) & (yy < -0.3)
        blocked[extreme_rim] = True
        
    elif scenario == "clear_plains":
        # Smooth lunar mare plains with minimal roughness and gentle undulations (< 6 deg)
        elevation = 3.0 * np.sin(0.4 * xx) * np.cos(0.4 * yy) + rng.normal(0, 0.1, (rows, cols))
        roughness = np.clip(0.08 + rng.uniform(0.0, 0.06, (rows, cols)), 0.0, 1.0)
        shadow = np.clip(0.1 + rng.uniform(0.0, 0.08, (rows, cols)), 0.0, 1.0)
        
    elif scenario == "shadow_valley":
        # Linear rift / graben valley running vertically with deep permanent shadow
        valley_dist = np.abs(xx - 0.2)
        valley_depth = -40.0 * np.exp(-4.0 * valley_dist**2)
        elevation += valley_depth
        
        # Permanently Shadowed Region (PSR) inside the valley floor
        valley_shadow = np.where(valley_dist < 0.5, 0.95, 0.0)
        shadow = np.clip(shadow + valley_shadow, 0.0, 1.0)
        roughness += np.where(valley_dist < 0.5, 0.35, 0.0)
        roughness = np.clip(roughness, 0.0, 1.0)
        
    elif scenario == "impassable_chasm":
        # Continuous barrier with no possible passage, testing robust no-path handling
        barrier_row = rows // 2
        elevation[barrier_row-1:barrier_row+2, :] += 60.0
        blocked[barrier_row-1:barrier_row+2, :] = True
        roughness[barrier_row-2:barrier_row+3, :] = 1.0

    # Calculate topographic slope in degrees using finite differences
    # Assuming spatial resolution of 10.0 meters per cell
    cell_size_m = 10.0
    grad_y, grad_x = np.gradient(elevation, cell_size_m)
    slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
    slope_deg = np.rad2deg(slope_rad)
    
    return {
        "elevation": elevation.astype(np.float64),
        "slope": slope_deg.astype(np.float64),
        "roughness": roughness.astype(np.float64),
        "shadow": shadow.astype(np.float64),
        "blocked": blocked,
        "metadata": {
            "source": "SIMULATED",
            "scenario": scenario,
            "cell_size_m": cell_size_m,
            "rows": rows,
            "cols": cols,
            "seed": seed,
            "disclaimer": "Synthetic procedural elevation model for route planning prototyping. Not for actual rover flight guidance."
        }
    }


def compute_cost_grid(
    terrain: Dict[str, Any],
    weights: Dict[str, float]
) -> np.ndarray:
    """
    Computes the cell traversal cost grid from terrain layers and mission weights.
    
    Formula:
        Cost = w_base + w_slope * (slope / max_slope)**2 + w_roughness * roughness + w_shadow * shadow
        
    Cells where slope exceeds max_slope_deg or marked blocked are assigned np.inf.
    
    Parameters:
        terrain: Dictionary returned by generate_synthetic_terrain.
        weights: Dictionary containing w_base, w_slope, w_roughness, w_shadow, max_slope_deg.
        
    Returns:
        2D np.ndarray of traversal costs per grid cell.
    """
    w_base = float(weights.get("w_base", 1.0))
    w_slope = float(weights.get("w_slope", 2.0))
    w_roughness = float(weights.get("w_roughness", 1.5))
    w_shadow = float(weights.get("w_shadow", 0.5))
    max_slope_deg = float(weights.get("max_slope_deg", 25.0))
    
    slope = terrain["slope"]
    roughness = terrain["roughness"]
    shadow = terrain["shadow"]
    blocked = terrain.get("blocked", np.zeros_like(slope, dtype=bool))
    
    # Normalized quadratic slope cost to penalize steeper angles progressively
    norm_slope = np.clip(slope / max(max_slope_deg, 1.0), 0.0, 2.0)
    slope_cost = w_slope * (norm_slope ** 2)
    
    roughness_cost = w_roughness * roughness
    shadow_cost = w_shadow * shadow
    
    cost_grid = w_base + slope_cost + roughness_cost + shadow_cost
    
    # Apply impassable thresholds
    is_impassable = blocked | (slope > max_slope_deg)
    cost_grid[is_impassable] = np.inf
    
    return cost_grid
