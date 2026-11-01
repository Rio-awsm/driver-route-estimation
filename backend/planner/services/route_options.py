from math import cos, radians

from ..clients import tomtom
from ..domain.geo import METERS_PER_MILE, MILES_PER_DEGREE_LAT, haversine_m
from ..exceptions import NoRouteFound, UpstreamError

REQUIRED_ROUTES = 3
SAME_ROUTE_OVERLAP = 0.95
OVERLAP_CELL_DEG = 0.05
VIA_OFFSET_SHARES = (0.15, -0.15, 0.3, -0.3)


def _footprint(route):
    return {
        (round(lat / OVERLAP_CELL_DEG), round(lon / OVERLAP_CELL_DEG)) for lat, lon in route.points
    }


def is_duplicate(route, others):
    footprint = _footprint(route)
    for other in others:
        other_footprint = _footprint(other)
        shared = len(footprint & other_footprint)
        if shared / min(len(footprint), len(other_footprint)) >= SAME_ROUTE_OVERLAP:
            return True
    return False


def via_point(route, offset_share):
    start, end = route.points[0], route.points[-1]
    middle = route.locate(route.length_m / 2)
    span_miles = haversine_m(start, end) / METERS_PER_MILE
    lon_scale = cos(radians(middle[0]))
    east = (end[1] - start[1]) * lon_scale
    north = end[0] - start[0]
    length = (east**2 + north**2) ** 0.5 or 1.0
    offset_deg = span_miles * offset_share / MILES_PER_DEGREE_LAT
    return (
        middle[0] + east / length * offset_deg,
        middle[1] - north / length * offset_deg / lon_scale,
    )


def get_route_options(origin, destination, departure, load_lb):
    ends = [(origin.lat, origin.lon), (destination.lat, destination.lon)]
    candidates = tomtom.calculate_routes(ends, departure, load_lb, alternatives=REQUIRED_ROUTES)
    if not candidates:
        raise NoRouteFound()

    routes = []
    for candidate in candidates:
        if not is_duplicate(candidate, routes):
            routes.append(candidate)

    for offset_share in VIA_OFFSET_SHARES:
        if len(routes) >= REQUIRED_ROUTES:
            break
        via = via_point(routes[0], offset_share)
        try:
            forced = tomtom.calculate_routes([ends[0], via, ends[1]], departure, load_lb, 0)
        except (NoRouteFound, UpstreamError):
            continue
        if forced and not is_duplicate(forced[0], routes):
            routes.append(forced[0])
    return routes[:REQUIRED_ROUTES]
