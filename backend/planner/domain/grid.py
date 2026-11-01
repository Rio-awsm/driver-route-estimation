from dataclasses import dataclass
from math import ceil, cos, floor, radians

from .geo import MILES_PER_DEGREE_LAT

# Degrees, finest first.
CHECKPOINT_STEPS = (0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0)
CORRIDOR_STEPS = (0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.75, 1.0, 1.5, 2.0, 3.0)
CORRIDOR_RADIUS_MILES = 40


def snap(lat, lon, step):
    return round(round(lat / step) * step, 4), round(round(lon / step) * step, 4)


def snap_to_budget(coordinates, budget):
    for step in CHECKPOINT_STEPS:
        cells = [snap(lat, lon, step) for lat, lon in coordinates]
        if len(set(cells)) <= budget:
            break
    return cells


@dataclass(frozen=True)
class Corridor:
    west: float
    south: float
    east: float
    north: float
    rows: int
    cols: int
    step: float
    cells: dict[tuple[int, int], tuple[float, float]]


def _mark_cells(paths, west, north, rows, cols, step, radius_miles):
    cells = {}
    radius_rows = ceil(radius_miles / (step * MILES_PER_DEGREE_LAT))
    for path in paths:
        for lat, lon in path:
            row = floor((north - lat) / step)
            col = floor((lon - west) / step)
            lon_scale = max(cos(radians(lat)), 0.2)
            radius_cols = ceil(radius_rows / lon_scale)
            for r in range(max(row - radius_rows, 0), min(row + radius_rows + 1, rows)):
                for c in range(max(col - radius_cols, 0), min(col + radius_cols + 1, cols)):
                    if (r, c) in cells:
                        continue
                    if (r - row) ** 2 + ((c - col) * lon_scale) ** 2 <= radius_rows**2:
                        cells[(r, c)] = (
                            round(north - (r + 0.5) * step, 4),
                            round(west + (c + 0.5) * step, 4),
                        )
    return cells


def build_corridor(paths, budget, radius_miles=CORRIDOR_RADIUS_MILES):
    lats = [lat for path in paths for lat, _ in path]
    lons = [lon for path in paths for _, lon in path]
    margin = radius_miles / MILES_PER_DEGREE_LAT * 1.5
    for step in CORRIDOR_STEPS:
        west = floor((min(lons) - margin) / step) * step
        east = ceil((max(lons) + margin) / step) * step
        south = floor((min(lats) - margin) / step) * step
        north = ceil((max(lats) + margin) / step) * step
        rows = round((north - south) / step)
        cols = round((east - west) / step)
        cells = _mark_cells(paths, west, north, rows, cols, step, radius_miles)
        if len(cells) <= budget:
            break
    return Corridor(west, south, east, north, rows, cols, step, cells)
