"""
pathfinding.py - A* Route Computation for Lunar Rover Navigation.

Compares:
1. Geometric Shortest Path (minimizing distance while avoiding blocked obstacles).
2. Hazard-Aware Optimal Path (minimizing accumulated terrain traversal cost).

All coordinates are consistently (row, col) tuples.
"""

from typing import List, Tuple, Dict, Any, Optional
import heapq
import math
import numpy as np


# 8-connected neighbor offsets with exact Euclidean step distance
NEIGHBOR_OFFSETS: List[Tuple[int, int, float]] = [
    (-1,  0, 1.0),
    ( 1,  0, 1.0),
    ( 0, -1, 1.0),
    ( 0,  1, 1.0),
    (-1, -1, math.sqrt(2.0)),
    (-1,  1, math.sqrt(2.0)),
    ( 1, -1, math.sqrt(2.0)),
    ( 1,  1, math.sqrt(2.0)),
]


def octile_distance(r1: int, c1: int, r2: int, c2: int) -> float:
    """
    Computes exact Octile distance heuristic for 8-connected grids.
    Admissible and consistent.
    """
    dr = abs(r1 - r2)
    dc = abs(c1 - c2)
    return (dr + dc) + (math.sqrt(2.0) - 2.0) * min(dr, dc)


def a_star_search(
    cost_grid: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    mode: str = "hazard_aware",
    cell_size_m: float = 10.0
) -> Dict[str, Any]:
    """
    Executes A* pathfinding on a 2D traversal cost grid.
    
    Parameters:
        cost_grid: 2D np.ndarray of cell traversal costs (np.inf for blocked/impassable).
        start: (row, col) tuple.
        goal: (row, col) tuple.
        mode: 'hazard_aware' (minimizes accumulated terrain cost) or
              'shortest' (minimizes geometric distance while avoiding np.inf cells).
        cell_size_m: Spatial resolution in meters per cell (default 10.0m).
        
    Returns:
        Dictionary containing:
            - success: bool
            - path: list of (row, col) tuples from start to goal (empty if no path)
            - distance: total geometric distance in meters
            - traversal_cost: accumulated traversal cost along the path
            - nodes_explored: number of expanded nodes
            - message: human-readable status explanation
    """
    rows, cols = cost_grid.shape
    start_r, start_c = start
    goal_r, goal_c = goal
    
    # 1. Bounds Validation
    if not (0 <= start_r < rows and 0 <= start_c < cols):
        return {
            "success": False,
            "path": [],
            "distance": 0.0,
            "traversal_cost": 0.0,
            "nodes_explored": 0,
            "message": f"Start coordinate ({start_r}, {start_c}) is outside grid boundaries (0-{rows-1}, 0-{cols-1})."
        }
        
    if not (0 <= goal_r < rows and 0 <= goal_c < cols):
        return {
            "success": False,
            "path": [],
            "distance": 0.0,
            "traversal_cost": 0.0,
            "nodes_explored": 0,
            "message": f"Goal coordinate ({goal_r}, {goal_c}) is outside grid boundaries (0-{rows-1}, 0-{cols-1})."
        }
        
    # 2. Blocked Cell Validation
    if np.isinf(cost_grid[start_r, start_c]):
        return {
            "success": False,
            "path": [],
            "distance": 0.0,
            "traversal_cost": 0.0,
            "nodes_explored": 0,
            "message": f"Start coordinate ({start_r}, {start_c}) lies on an impassable hazard cell."
        }
        
    if np.isinf(cost_grid[goal_r, goal_c]):
        return {
            "success": False,
            "path": [],
            "distance": 0.0,
            "traversal_cost": 0.0,
            "nodes_explored": 0,
            "message": f"Goal coordinate ({goal_r}, {goal_c}) lies on an impassable hazard cell."
        }
        
    # 3. Trivial Case: Start is Goal
    if start == goal:
        return {
            "success": True,
            "path": [start],
            "distance": 0.0,
            "traversal_cost": float(cost_grid[start_r, start_c]),
            "nodes_explored": 1,
            "message": "Rover is already located at the destination coordinate."
        }

    # Minimum traversable cost for admissible heuristic scaling
    finite_mask = np.isfinite(cost_grid)
    min_cost = float(np.min(cost_grid[finite_mask])) if np.any(finite_mask) else 1.0
    min_cost = max(min_cost, 0.01)
    
    # Priority Queue: (f_score, tie_breaker, current_node)
    counter = 0
    open_heap = []
    
    # Heuristic function
    def compute_h(r: int, c: int) -> float:
        oct_dist = octile_distance(r, c, goal_r, goal_c)
        if mode == "hazard_aware":
            return oct_dist * cell_size_m * min_cost
        else:
            return oct_dist * cell_size_m

    h_start = compute_h(start_r, start_c)
    heapq.heappush(open_heap, (h_start, counter, start))
    
    # Cost-so-far tracking: g_score is the primary optimization objective
    g_score: Dict[Tuple[int, int], float] = {start: 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    closed_set = set()
    nodes_explored = 0

    while open_heap:
        current_f, _, current = heapq.heappop(open_heap)
        
        if current in closed_set:
            continue
            
        closed_set.add(current)
        nodes_explored += 1
        
        if current == goal:
            # Reconstruct Path
            path: List[Tuple[int, int]] = []
            curr_node = goal
            while curr_node in came_from:
                path.append(curr_node)
                curr_node = came_from[curr_node]
            path.append(start)
            path.reverse()
            
            # Compute exact geometric distance and accumulated traversal cost
            total_dist_m = 0.0
            total_traversal_cost = 0.0
            
            for i in range(len(path) - 1):
                p1 = path[i]
                p2 = path[i + 1]
                dr = abs(p1[0] - p2[0])
                dc = abs(p1[1] - p2[1])
                step_units = math.sqrt(2.0) if (dr > 0 and dc > 0) else 1.0
                step_m = step_units * cell_size_m
                
                c1 = float(cost_grid[p1[0], p1[1]])
                c2 = float(cost_grid[p2[0], p2[1]])
                avg_cost = (c1 + c2) / 2.0
                
                total_dist_m += step_m
                total_traversal_cost += step_m * avg_cost
                
            return {
                "success": True,
                "path": path,
                "distance": round(total_dist_m, 2),
                "traversal_cost": round(total_traversal_cost, 2),
                "nodes_explored": nodes_explored,
                "message": f"Successfully computed {mode} route ({len(path)} waypoints)."
            }

        cr, cc = current
        for dr, dc, step_mult in NEIGHBOR_OFFSETS:
            nr, nc = cr + dr, cc + dc
            neighbor = (nr, nc)
            
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
                
            if neighbor in closed_set:
                continue
                
            n_cost = float(cost_grid[nr, nc])
            if np.isinf(n_cost):
                continue
                
            # Step metric
            step_m = step_mult * cell_size_m
            if mode == "hazard_aware":
                curr_cost = float(cost_grid[cr, cc])
                transition_cost = step_m * ((curr_cost + n_cost) / 2.0)
            else:
                # Geometric shortest path: cost is purely physical distance
                transition_cost = step_m

            tentative_g = g_score[current] + transition_cost
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                f_score = tentative_g + compute_h(nr, nc)
                counter += 1
                heapq.heappush(open_heap, (f_score, counter, neighbor))

    return {
        "success": False,
        "path": [],
        "distance": 0.0,
        "traversal_cost": 0.0,
        "nodes_explored": nodes_explored,
        "message": "No navigable path found between coordinates. Path is blocked by impassable terrain."
    }


def compute_routes(
    cost_grid: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    cell_size_m: float = 10.0
) -> Dict[str, Any]:
    """
    Computes both Shortest Path and Hazard-Aware Path concurrently for side-by-side comparison.
    """
    shortest_res = a_star_search(cost_grid, start, goal, mode="shortest", cell_size_m=cell_size_m)
    hazard_res = a_star_search(cost_grid, start, goal, mode="hazard_aware", cell_size_m=cell_size_m)
    
    return {
        "shortest": shortest_res,
        "hazard_aware": hazard_res
    }
