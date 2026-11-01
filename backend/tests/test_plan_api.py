import base64
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from planner.clients import open_meteo, tomtom
from planner.domain.geo import METERS_PER_MILE
from planner.domain.models import RoutePath
from planner.domain.weather import HourlySeries
from planner.exceptions import NoRouteFound, UpstreamError, WeatherRateLimited
from planner.services import route_options

CHICAGO = {"label": "Chicago, IL", "lat": 41.88, "lon": -87.63}
DENVER = {"label": "Denver, CO", "lat": 39.74, "lon": -104.99}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def bent_route(bend_lat, hours):
    points = [(41.88, -87.63), (bend_lat, -96.3), (39.74, -104.99)]
    length = 1000 * METERS_PER_MILE
    return RoutePath(
        points=points,
        distance_m=[0.0, length / 2, length],
        time_s=[0.0, hours * 1800, hours * 3600],
    )


def calm_series(start, end):
    hours = int((end - start).total_seconds() // 3600) + 1
    return HourlySeries(
        times=[int(start.timestamp()) + hour * 3600 for hour in range(hours)],
        wind_mph=[5.0] * hours,
        gust_mph=[8.0] * hours,
        rain_in=[0.0] * hours,
        snow_in=[0.0] * hours,
    )


@pytest.fixture
def fake_weather(monkeypatch):
    def fetch(cells, start, end):
        fetch.locations = len(set(cells))
        fetch.end = end
        windy = calm_series(start, end)
        windy = HourlySeries(
            windy.times, [50.0] * len(windy.times), windy.gust_mph, windy.rain_in, windy.snow_in
        )
        return {
            cell: (windy if cell[0] < fetch.storm_below else calm_series(start, end))
            for cell in set(cells)
        }

    fetch.storm_below = -90
    fetch.locations = 0
    monkeypatch.setattr(open_meteo, "fetch_series", fetch)
    return fetch


@pytest.fixture
def fake_routes(monkeypatch):
    routes = [bent_route(41.0, 17), bent_route(37.0, 18), bent_route(45.0, 19)]
    monkeypatch.setattr(tomtom, "calculate_routes", lambda *args, **kwargs: routes)
    return routes


def payload(**overrides):
    return {
        "origin": CHICAGO,
        "destination": DENVER,
        "departure": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_lb": 35_000,
        "interval_miles": 25,
        **overrides,
    }


def post_plan(**overrides):
    return APIClient().post("/api/plan", payload(**overrides), format="json")


def test_plan_returns_three_ranked_routes(fake_routes, fake_weather):
    response = post_plan()
    body = response.json()
    assert response.status_code == 200
    assert [route["id"] for route in body["routes"]] == ["A", "B", "C"]
    assert body["recommended_route"] == "A"
    assert "travel time" in body["reason"]


def test_checkpoints_cover_the_whole_route(fake_routes, fake_weather):
    route = post_plan().json()["routes"][0]
    assert route["checkpoints"][0]["mile"] == 0
    assert route["checkpoints"][-1]["mile"] == pytest.approx(route["distance_miles"])
    assert len(route["segments"]) == len(route["checkpoints"])


def test_storm_on_the_fastest_route_changes_the_recommendation(fake_routes, fake_weather):
    fake_weather.storm_below = 39.0
    body = post_plan().json()
    routes = {route["id"]: route for route in body["routes"]}
    assert routes["C"]["no_travel_miles"] == 0
    assert routes["B"]["no_travel_miles"] > 0
    assert body["recommended_route"] in ("A", "C")
    assert body["routes"][-1]["id"] == "B"


def test_every_route_blocked_sets_the_flag(fake_routes, fake_weather):
    fake_weather.storm_below = 90
    body = post_plan().json()
    assert body["blocked"] is True
    assert body["reason"].startswith("Do not depart")


def test_heatmap_shape_matches_its_header(fake_routes, fake_weather):
    heatmap = post_plan().json()["heatmap"]
    levels = base64.b64decode(heatmap["levels"])
    assert len(levels) == heatmap["rows"] * heatmap["cols"] * 49
    assert 0 in levels and 255 in levels


def test_plan_stays_under_the_minute_limit(fake_routes, fake_weather):
    post_plan(interval_miles=10)
    assert 0 < fake_weather.locations <= 550


def test_missing_alternatives_are_forced_with_a_via_point(monkeypatch, fake_weather):
    first = bent_route(41.0, 17)

    def calculate(waypoints, departure, load_lb, alternatives):
        if len(waypoints) == 2:
            return [first]
        via_lat = waypoints[1][0]
        if via_lat > 41:
            return [bent_route(45.0, 19)]
        raise NoRouteFound()

    monkeypatch.setattr(tomtom, "calculate_routes", calculate)
    routes = route_options.get_route_options(
        type("P", (), CHICAGO), type("P", (), DENVER), timezone.now(), 10_000
    )
    assert len(routes) == 2


def test_failed_detour_keeps_the_routes_already_found(monkeypatch, fake_weather):
    def calculate(waypoints, departure, load_lb, alternatives):
        if len(waypoints) == 2:
            return [bent_route(41.0, 17)]
        raise UpstreamError()

    monkeypatch.setattr(tomtom, "calculate_routes", calculate)
    response = post_plan()
    assert response.status_code == 200
    assert len(response.json()["routes"]) == 1


def test_offset_departure_is_read_in_utc(fake_routes, fake_weather):
    india = dt_timezone(timedelta(hours=5, minutes=30))
    departure = (timezone.now() + timedelta(hours=2)).astimezone(india)
    body = post_plan(departure=departure.isoformat()).json()
    expected = departure.astimezone(dt_timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = datetime.fromisoformat(body["heatmap"]["start"])
    assert start == expected
    assert start.utcoffset() == timedelta(0)


def test_trip_longer_than_the_heatmap_keeps_its_forecast(monkeypatch, fake_weather):
    route = bent_route(41.0, 60)
    monkeypatch.setattr(tomtom, "calculate_routes", lambda *args, **kwargs: [route])
    body = post_plan().json()
    arrival = datetime.fromisoformat(body["routes"][0]["arrival"])
    assert fake_weather.end >= arrival
    assert body["heatmap"]["hours"] == 49


def test_very_short_trip_still_plans(monkeypatch, fake_weather):
    route = RoutePath(
        points=[(41.88, -87.63), (41.881, -87.63)],
        distance_m=[0.0, 120.0],
        time_s=[0.0, 30.0],
    )
    monkeypatch.setattr(tomtom, "calculate_routes", lambda *args, **kwargs: [route])
    response = post_plan()
    assert response.status_code == 200
    assert len(response.json()["routes"][0]["checkpoints"]) == 2


@pytest.mark.parametrize(
    "error, status",
    [(NoRouteFound, 422), (UpstreamError, 502), (WeatherRateLimited, 503)],
)
def test_provider_failures_reach_the_browser_as_clean_errors(monkeypatch, error, status):
    def fail(*args, **kwargs):
        raise error()

    monkeypatch.setattr(tomtom, "calculate_routes", fail)
    response = post_plan()
    assert response.status_code == status
    assert response.json() == {"detail": error.default_detail}


def test_duplicate_alternatives_are_dropped():
    route = bent_route(41.0, 17)
    assert route_options.is_duplicate(route, [bent_route(41.0, 20)]) is True
    assert route_options.is_duplicate(route, [bent_route(45.0, 20)]) is False


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"load_lb": -1}, "load_lb"),
        ({"interval_miles": 30}, "interval_miles"),
        ({"departure": "2020-01-01T00:00:00Z"}, "departure"),
        ({"departure": "2099-01-01T00:00:00Z"}, "departure"),
    ],
)
def test_bad_input_is_rejected(overrides, field):
    response = post_plan(**overrides)
    assert response.status_code == 400
    assert field in response.json()


def test_same_origin_and_destination_is_rejected():
    assert post_plan(destination=CHICAGO).status_code == 400


def test_short_geocode_query_skips_the_provider():
    response = APIClient().get("/api/geocode", {"q": "ab"})
    assert response.json() == {"results": []}

