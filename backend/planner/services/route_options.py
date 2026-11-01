from math import cos, radians

from ..clients import tomtom
from ..domain.geo import METERS_PER_MILE, MILES_PER_DEGREE_LAT, haversine_m
from ..exceptions import NoRouteFound, UpstreamError

REQUIRED_ROUTES = 3
SAME_ROUTE_OVERLAP = 0.95
OVERLAP_CELL_DEG = 0.05
ROUTE_VARIANTS = ({"routeType": "shortest"}, {"avoid": "tollRoads"}, {"avoid": "motorways"})
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


def _add_if_new(routes, waypoints, departure, load_lb, options=None):
    try:
        found = tomtom.calculate_routes(waypoints, departure, load_lb, 0, options)
    except (NoRouteFound, UpstreamError):
        return
    if found and not is_duplicate(found[0], routes):
        routes.append(found[0])


def get_route_options(origin, destination, departure, load_lb):
    ends = [(origin.lat, origin.lon), (destination.lat, destination.lon)]
    candidates = tomtom.calculate_routes(ends, departure, load_lb, alternatives=REQUIRED_ROUTES)
    if not candidates:
        raise NoRouteFound()

    routes = []
    for candidate in candidates:
        if not is_duplicate(candidate, routes):
            routes.append(candidate)

    for options in ROUTE_VARIANTS:
        if len(routes) >= REQUIRED_ROUTES:
            break
        _add_if_new(routes, ends, departure, load_lb, options)

    for offset_share in VIA_OFFSET_SHARES:
        if len(routes) >= REQUIRED_ROUTES:
            break
        _add_if_new(routes, [ends[0], via_point(routes[0], offset_share), ends[1]], departure, load_lb)
    return routes[:REQUIRED_ROUTES]
