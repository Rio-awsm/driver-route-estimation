from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote

import httpx
import pytest
import respx
from django.core.cache import cache

from planner.clients import open_meteo, tomtom
from planner.exceptions import NoRouteFound, UpstreamError, WeatherRateLimited

START = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
END = datetime(2026, 11, 2, 14, tzinfo=timezone.utc)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def tomtom_route():
    return {
        "summary": {"lengthInMeters": 2000, "travelTimeInSeconds": 120},
        "legs": [
            {"points": [{"latitude": 40.0, "longitude": -100.0}, {"latitude": 40.0, "longitude": -99.99}]},
            {"points": [{"latitude": 40.0, "longitude": -99.98}]},
        ],
        "progress": [
            {"pointIndex": 0, "distanceInMeters": 0, "travelTimeInSeconds": 0},
            {"pointIndex": 2, "distanceInMeters": 2000, "travelTimeInSeconds": 120},
        ],
    }


def location(wind=10.0):
    return {
        "hourly": {
            "time": [1, 2, 3],
            "wind_speed_10m": [wind, wind, wind],
            "wind_gusts_10m": [wind, wind, None],
            "rain": [0.1, 0.0, None],
            "showers": [0.2, 0.0, 0.0],
            "snowfall": [0.0, 0.0, 0.0],
        }
    }


def test_parse_route_fills_every_point_from_progress():
    route = tomtom.parse_route(tomtom_route())
    assert len(route.points) == 3
    assert route.distance_m[1] == pytest.approx(1000)
    assert route.time_s[1] == pytest.approx(60)
    assert route.length_m == 2000


@respx.mock
def test_calculate_routes_sends_truck_parameters():
    url = "https://api.tomtom.com/routing/1/calculateRoute/40.000000,-100.000000:41.000000,-99.000000/json"
    call = respx.get(url).mock(
        return_value=httpx.Response(200, json={"routes": [tomtom_route()]})
    )
    routes = tomtom.calculate_routes([(40, -100), (41, -99)], START, 10_000, alternatives=3)
    query = parse_qs(call.calls[0].request.url.query.decode())
    assert len(routes) == 1
    assert query["travelMode"] == ["truck"]
    assert query["vehicleWeight"] == [str(round(45_000 * 0.45359237))]
    assert query["maxAlternatives"] == ["3"]
    assert query["extendedRouteRepresentation"] == ["distance", "travelTime"]


@respx.mock
def test_route_blocked_by_truck_length_retries_at_the_short_length():
    call = respx.get(url__regex=r".*calculateRoute.*").mock(
        side_effect=[
            httpx.Response(400, json={"detailedError": {"code": "NO_ROUTE_FOUND"}}),
            httpx.Response(200, json={"routes": [tomtom_route()]}),
        ]
    )
    routes = tomtom.calculate_routes([(59.9, 10.7), (69.6, 18.9)], START, 10_000, alternatives=0)
    lengths = [parse_qs(request.request.url.query.decode())["vehicleLength"] for request in call.calls]
    assert len(routes) == 1
    assert lengths == [["21.0"], ["16.5"]]


@respx.mock
def test_point_off_the_road_does_not_retry():
    call = respx.get(url__regex=r".*calculateRoute.*").mock(
        return_value=httpx.Response(400, json={"detailedError": {"code": "MAP_MATCHING_FAILURE"}})
    )
    with pytest.raises(NoRouteFound):
        tomtom.calculate_routes([(40, -100), (41, -99)], START, 0, alternatives=0)
    assert call.call_count == 1


@respx.mock
def test_route_options_are_sent_to_tomtom():
    call = respx.get(url__regex=r".*calculateRoute.*").mock(
        return_value=httpx.Response(200, json={"routes": [tomtom_route()]})
    )
    tomtom.calculate_routes([(40, -100), (41, -99)], START, 0, 0, {"avoid": "tollRoads"})
    assert parse_qs(call.calls[0].request.url.query.decode())["avoid"] == ["tollRoads"]


@respx.mock
def test_routing_400_means_no_route():
    respx.get(url__regex=r".*calculateRoute.*").mock(return_value=httpx.Response(400))
    with pytest.raises(NoRouteFound):
        tomtom.calculate_routes([(40, -100), (41, -99)], START, 0, alternatives=0)


@respx.mock
def test_search_places_maps_results_and_encodes_the_query():
    call = respx.get(url__regex=r".*/search/2/search/.*").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "address": {"freeformAddress": "Chicago, IL"},
                        "position": {"lat": 41.88, "lon": -87.63},
                    }
                ]
            },
        )
    )
    assert tomtom.search_places("St. Louis, MO?")[0] == {"label": "Chicago, IL", "lat": 41.88, "lon": -87.63}
    assert unquote(call.calls[0].request.url.path).endswith("/St. Louis, MO?.json")


@respx.mock
def test_search_labels_name_the_country_once():
    call = respx.get(url__regex=r".*/search/2/search/.*").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "address": {"freeformAddress": "Tokyo", "country": "Japan"},
                        "position": {"lat": 35.6, "lon": 139.7},
                    },
                    {
                        "address": {"freeformAddress": "Delhi, India", "country": "India"},
                        "position": {"lat": 28.6, "lon": 77.2},
                    },
                ]
            },
        )
    )
    labels = [place["label"] for place in tomtom.search_places("To")]
    query = parse_qs(call.calls[0].request.url.query.decode())
    assert labels == ["Tokyo, Japan", "Delhi, India"]
    assert query["language"] == ["en-GB"]
    assert "countrySet" not in query


def test_parse_series_adds_showers_and_clears_nulls():
    series = open_meteo.parse_series(location())
    assert series.rain_in == pytest.approx([0.3, 0.0, 0.0])
    assert series.gust_mph[2] == 0.0


@respx.mock
def test_fetch_series_batches_and_uses_inches_and_mph():
    call = respx.post(FORECAST_URL).mock(
        side_effect=lambda request: httpx.Response(
            200, json=[location() for _ in parse_qs(request.content.decode())["latitude"][0].split(",")]
        )
    )
    cells = [(30.0 + index, -100.0) for index in range(205)]
    series = open_meteo.fetch_series(cells, START, END)
    body = parse_qs(call.calls[0].request.content.decode())
    assert len(series) == 205
    assert call.call_count == 2
    assert body["wind_speed_unit"] == ["mph"]
    assert body["precipitation_unit"] == ["inch"]
    assert body["start_hour"] == ["2026-11-02T12:00"]


@respx.mock
def test_single_location_response_is_an_object():
    respx.post(FORECAST_URL).mock(return_value=httpx.Response(200, json=location()))
    assert len(open_meteo.fetch_series([(30.0, -100.0)], START, END)) == 1


@respx.mock
def test_second_fetch_comes_from_cache():
    call = respx.post(FORECAST_URL).mock(return_value=httpx.Response(200, json=location()))
    open_meteo.fetch_series([(30.0, -100.0)], START, END)
    open_meteo.fetch_series([(30.0, -100.0)], START, END)
    assert call.call_count == 1


@respx.mock
def test_rate_limit_retries_then_gives_a_clear_error(monkeypatch):
    monkeypatch.setattr(open_meteo.time, "sleep", lambda seconds: None)
    call = respx.post(FORECAST_URL).mock(return_value=httpx.Response(429))
    with pytest.raises(WeatherRateLimited):
        open_meteo.fetch_series([(30.0, -100.0)], START, END)
    assert call.call_count == 3


@respx.mock
def test_server_error_is_reported_as_upstream():
    respx.post(FORECAST_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(UpstreamError):
        open_meteo.fetch_series([(30.0, -100.0)], START, END)
