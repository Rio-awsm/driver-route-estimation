from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from django.conf import settings

from ..domain.geo import haversine_m
from ..domain.models import RoutePath
from ..exceptions import NoRouteFound, UpstreamError

BASE_URL = "https://api.tomtom.com"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
KG_PER_LB = 0.45359237

# Typical US tractor-trailer.
TRACTOR_TRAILER_TARE_LB = 35_000
TRUCK_PROFILE = {
    "vehicleCommercial": "true",
    "vehicleLength": 21.0,
    "vehicleWidth": 2.6,
    "vehicleHeight": 4.1,
    "vehicleNumberOfAxles": 5,
    "vehicleMaxSpeed": 105,
}


def _expand_progress(points, progress):
    distance_m = [0.0] * len(points)
    time_s = [0.0] * len(points)
    for start, end in zip(progress, progress[1:]):
        first, last = start["pointIndex"], min(end["pointIndex"], len(points) - 1)
        steps = [haversine_m(points[i], points[i + 1]) for i in range(first, last)]
        total = sum(steps) or 1.0
        travelled = 0.0
        for offset, step in enumerate(steps, start=1):
            travelled += step
            share = travelled / total
            distance_m[first + offset] = start["distanceInMeters"] + share * (
                end["distanceInMeters"] - start["distanceInMeters"]
            )
            time_s[first + offset] = start["travelTimeInSeconds"] + share * (
                end["travelTimeInSeconds"] - start["travelTimeInSeconds"]
            )
    return distance_m, time_s


def parse_route(raw):
    points = [
        (point["latitude"], point["longitude"]) for leg in raw["legs"] for point in leg["points"]
    ]
    distance_m, time_s = _expand_progress(points, raw["progress"])
    return RoutePath(points=points, distance_m=distance_m, time_s=time_s)


def calculate_routes(waypoints, departure, load_lb, alternatives):
    locations = ":".join(f"{lat:.6f},{lon:.6f}" for lat, lon in waypoints)
    depart_at = max(departure, datetime.now(timezone.utc))
    params = {
        **TRUCK_PROFILE,
        "key": settings.TOMTOM_API_KEY,
        "travelMode": "truck",
        "routeType": "fastest",
        "traffic": "true",
        "departAt": depart_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vehicleWeight": round((TRACTOR_TRAILER_TARE_LB + load_lb) * KG_PER_LB),
        "maxAlternatives": alternatives,
        "routeRepresentation": "polyline",
        "extendedRouteRepresentation": ["distance", "travelTime"],
    }
    url = f"{BASE_URL}/routing/1/calculateRoute/{locations}/json"
    try:
        response = httpx.get(url, params=params, timeout=TIMEOUT)
    except httpx.HTTPError as error:
        raise UpstreamError("The routing provider could not be reached.") from error
    if response.status_code in (400, 404):
        raise NoRouteFound()
    if response.status_code != 200:
        raise UpstreamError(f"The routing provider returned {response.status_code}.")
    return [parse_route(route) for route in response.json()["routes"]]


def search_places(query, limit=5):
    url = f"{BASE_URL}/search/2/search/{quote(query, safe='')}.json"
    params = {
        "key": settings.TOMTOM_API_KEY,
        "typeahead": "true",
        "limit": limit,
        "countrySet": "US,CA",
        "idxSet": "Geo,Addr,PAD",
    }
    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise UpstreamError("Address search is unavailable.") from error
    return [
        {
            "label": result["address"]["freeformAddress"],
            "lat": result["position"]["lat"],
            "lon": result["position"]["lon"],
        }
        for result in response.json().get("results", [])
    ]
