import base64
from datetime import timedelta

from ..clients import open_meteo
from ..domain.checkpoints import sample_checkpoints
from ..domain.geo import METERS_PER_MILE, simplify
from ..domain.grid import build_corridor, snap_to_budget
from ..domain.ranking import explain, rank_routes, score_route
from ..domain.risk import classify
from .route_options import get_route_options

# Open-Meteo's free tier allows 600 locations a minute.
MAX_WEATHER_LOCATIONS = 550
MAX_CHECKPOINT_LOCATIONS = 350

HEATMAP_HOURS = 49
NO_DATA = 255
ROUTE_IDS = "ABC"
SEGMENT_TOLERANCE_DEG = 0.002
CORRIDOR_SAMPLE_M = 8000


def _floor_hour(moment):
    return moment.replace(minute=0, second=0, microsecond=0)


def _ceil_hour(moment):
    return _floor_hour(moment) + timedelta(hours=1)


def _sampled_path(route):
    path = []
    distance = 0.0
    while distance < route.length_m:
        path.append(route.locate(distance)[:2])
        distance += CORRIDOR_SAMPLE_M
    path.append(route.points[-1])
    return path


def _score_checkpoints(checkpoints, cells, series, load_lb):
    scored = []
    for checkpoint, cell in zip(checkpoints, cells):
        conditions = series[cell].at(checkpoint.eta.timestamp())
        level, driver = classify(
            conditions.wind_mph, conditions.rain_in_hr, conditions.snow_in_hr, load_lb
        )
        scored.append((checkpoint, conditions, level, driver))
    return scored


def _checkpoint_json(checkpoint, conditions, level, driver):
    return {
        "mile": round(checkpoint.mile, 1),
        "lat": round(checkpoint.lat, 5),
        "lon": round(checkpoint.lon, 5),
        "eta": checkpoint.eta.isoformat(),
        "wind_mph": round(conditions.wind_mph, 1),
        "gust_mph": round(conditions.gust_mph, 1),
        "rain_in_hr": round(conditions.rain_in_hr, 3),
        "snow_in_hr": round(conditions.snow_in_hr, 3),
        "risk": int(level),
        "risk_label": level.label,
        "risk_driver": driver,
    }


def _segments_json(route, scored):
    segments = []
    for checkpoint, _, level, _ in scored:
        path = simplify(route.slice(checkpoint.from_m, checkpoint.to_m), SEGMENT_TOLERANCE_DEG)
        segments.append(
            {
                "risk": int(level),
                "path": [[round(lon, 5), round(lat, 5)] for lat, lon in path],
            }
        )
    return segments


def _route_json(route_id, route, score, scored, departure):
    return {
        "id": route_id,
        "distance_miles": round(route.length_m / METERS_PER_MILE, 1),
        "duration_s": round(route.duration_s),
        "arrival": (departure + timedelta(seconds=route.duration_s)).isoformat(),
        "no_travel_miles": round(score.no_travel_miles, 1),
        "severe_miles": round(score.severe_miles, 1),
        "high_miles": round(score.high_miles, 1),
        "average_risk": round(score.average_risk, 2),
        "checkpoints": [_checkpoint_json(*item) for item in scored],
        "segments": _segments_json(route, scored),
    }


def _heatmap_json(corridor, series, start, load_lb):
    levels = bytearray([NO_DATA]) * (corridor.rows * corridor.cols * HEATMAP_HOURS)
    start_s = start.timestamp()
    for (row, col), cell in corridor.cells.items():
        offset = row * corridor.cols + col
        for hour in range(HEATMAP_HOURS):
            conditions = series[cell].at(start_s + hour * 3600)
            level, _ = classify(
                conditions.wind_mph, conditions.rain_in_hr, conditions.snow_in_hr, load_lb
            )
            levels[hour * corridor.rows * corridor.cols + offset] = level
    return {
        "bounds": [corridor.west, corridor.south, corridor.east, corridor.north],
        "rows": corridor.rows,
        "cols": corridor.cols,
        "hours": HEATMAP_HOURS,
        "start": start.isoformat(),
        "levels": base64.b64encode(bytes(levels)).decode(),
    }


def build_plan(origin, destination, departure, load_lb, interval_miles):
    routes = get_route_options(origin, destination, departure, load_lb)
    checkpoints = [sample_checkpoints(route, interval_miles, departure) for route in routes]

    coordinates = [(cp.lat, cp.lon) for route_cps in checkpoints for cp in route_cps]
    checkpoint_cells = snap_to_budget(coordinates, MAX_CHECKPOINT_LOCATIONS)
    corridor = build_corridor(
        [_sampled_path(route) for route in routes],
        budget=MAX_WEATHER_LOCATIONS - len(set(checkpoint_cells)),
    )

    start = _floor_hour(departure)
    last_eta = max(route_cps[-1].eta for route_cps in checkpoints)
    end = max(start + timedelta(hours=HEATMAP_HOURS - 1), _ceil_hour(last_eta))
    series = open_meteo.fetch_series([*checkpoint_cells, *corridor.cells.values()], start, end)

    payloads, scores = {}, []
    position = 0
    for route_id, route, route_cps in zip(ROUTE_IDS, routes, checkpoints):
        cells = checkpoint_cells[position : position + len(route_cps)]
        position += len(route_cps)
        scored = _score_checkpoints(route_cps, cells, series, load_lb)
        stretches = [(cp.covered_miles, level) for cp, _, level, _ in scored]
        score = score_route(route_id, stretches, route.duration_s)
        scores.append(score)
        payloads[route_id] = _route_json(route_id, route, score, scored, departure)

    ranked = rank_routes(scores)
    best = ranked[0]
    return {
        "departure": departure.isoformat(),
        "load_lb": load_lb,
        "interval_miles": interval_miles,
        "recommended_route": best.route_id,
        "blocked": best.no_travel_miles > 0,
        "reason": explain(ranked),
        "routes": [payloads[score.route_id] for score in ranked],
        "heatmap": _heatmap_json(corridor, series, start, load_lb),
    }
