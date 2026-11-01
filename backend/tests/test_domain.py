from datetime import datetime, timedelta, timezone
from math import sin

import pytest

from planner.domain.checkpoints import sample_checkpoints
from planner.domain.geo import METERS_PER_MILE, haversine_m, simplify
from planner.domain.grid import build_corridor, snap_to_budget
from planner.domain.models import RoutePath
from planner.domain.weather import HourlySeries

DEPARTURE = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def straight_route(miles, mph=60):
    length_m = miles * METERS_PER_MILE
    end = (0.0, length_m / 111_195)
    return RoutePath(
        points=[(0.0, 0.0), end],
        distance_m=[0.0, length_m],
        time_s=[0.0, miles / mph * 3600],
    )


def test_haversine_one_degree_of_latitude():
    assert haversine_m((0, 0), (1, 0)) == pytest.approx(111_195, abs=5)


def test_checkpoints_start_and_end_at_the_trip_ends():
    points = sample_checkpoints(straight_route(100), 25, DEPARTURE)
    assert [round(point.mile) for point in points] == [0, 25, 50, 75, 100]


def test_short_final_stretch_keeps_the_destination():
    points = sample_checkpoints(straight_route(60), 25, DEPARTURE)
    assert [round(point.mile) for point in points] == [0, 25, 50, 60]


def test_destination_just_past_a_checkpoint_replaces_it():
    points = sample_checkpoints(straight_route(50.04), 25, DEPARTURE)
    assert [round(point.mile, 1) for point in points] == [0, 25, 50.0]
    assert sum(point.covered_miles for point in points) == pytest.approx(50.04)


def test_exact_multiple_ends_once_at_the_destination():
    points = sample_checkpoints(straight_route(1450), 50, DEPARTURE)
    assert [round(point.mile) for point in points] == list(range(0, 1451, 50))


def test_each_checkpoint_owns_the_road_nearest_to_it():
    points = sample_checkpoints(straight_route(100), 25, DEPARTURE)
    assert [point.covered_miles for point in points] == pytest.approx([12.5, 25, 25, 25, 12.5])


def test_covered_miles_sum_to_route_length():
    points = sample_checkpoints(straight_route(137), 10, DEPARTURE)
    assert sum(point.covered_miles for point in points) == pytest.approx(137)


def test_eta_follows_route_time():
    points = sample_checkpoints(straight_route(120, mph=60), 60, DEPARTURE)
    assert [point.eta for point in points] == [
        DEPARTURE,
        DEPARTURE + timedelta(hours=1),
        DEPARTURE + timedelta(hours=2),
    ]


def test_eta_uses_uneven_speeds_not_an_average():
    route = RoutePath(
        points=[(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)],
        distance_m=[0.0, 100_000.0, 200_000.0],
        time_s=[0.0, 3600.0, 4600.0],
    )
    middle = sample_checkpoints(route, 100_000 / METERS_PER_MILE, DEPARTURE)[1]
    assert middle.eta == DEPARTURE + timedelta(hours=1)


def test_route_reports_length_and_duration():
    route = straight_route(120, mph=60)
    assert route.length_m == pytest.approx(120 * METERS_PER_MILE)
    assert route.duration_s == pytest.approx(7200)


def test_slice_keeps_inner_points_and_interpolates_the_ends():
    route = RoutePath(
        points=[(0.0, 0.0), (0.0, 1.0), (0.0, 2.0), (0.0, 3.0)],
        distance_m=[0.0, 100.0, 200.0, 300.0],
        time_s=[0.0, 10.0, 20.0, 30.0],
    )
    assert route.slice(50, 250) == [(0.0, 0.5), (0.0, 1.0), (0.0, 2.0), (0.0, 2.5)]


def test_slice_does_not_repeat_a_point_on_the_cut():
    route = RoutePath(
        points=[(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)],
        distance_m=[0.0, 100.0, 200.0],
        time_s=[0.0, 10.0, 20.0],
    )
    assert route.slice(100, 200) == [(0.0, 1.0), (0.0, 2.0)]


def test_arrival_time_survives_a_zero_length_final_segment():
    route = RoutePath(
        points=[(0.0, 0.0), (0.0, 1.0), (0.0, 1.0)],
        distance_m=[0.0, 100.0, 100.0],
        time_s=[0.0, 10.0, 15.0],
    )
    assert route.locate(100)[2] == 15.0


def test_departure_time_survives_a_zero_length_first_segment():
    route = RoutePath(
        points=[(0.0, 0.0), (0.0, 0.0), (0.0, 1.0)],
        distance_m=[0.0, 0.0, 100.0],
        time_s=[0.0, 5.0, 15.0],
    )
    assert route.locate(0)[2] == 0.0


def test_locate_interpolates_position_and_time():
    route = RoutePath(
        points=[(10.0, 20.0), (12.0, 26.0)],
        distance_m=[0.0, 100.0],
        time_s=[0.0, 10.0],
    )
    assert route.locate(25) == pytest.approx((10.5, 21.5, 2.5))


def test_locate_clamps_to_the_route():
    route = straight_route(100)
    assert route.locate(-50)[2] == 0
    assert route.locate(route.length_m + 50)[:2] == route.points[-1]


SERIES = HourlySeries(
    times=[0, 3600, 7200],
    wind_mph=[10.0, 20.0, 40.0],
    gust_mph=[15.0, 25.0, 45.0],
    rain_in=[0.0, 0.3, 0.0],
    snow_in=[0.0, 0.0, 1.5],
)


def test_wind_is_interpolated_between_hours():
    assert SERIES.at(1800).wind_mph == 15.0


def test_rain_reads_the_hour_that_covers_the_arrival():
    assert SERIES.at(1).rain_in_hr == 0.3
    assert SERIES.at(3601).rain_in_hr == 0.0
    assert SERIES.at(3601).snow_in_hr == 1.5


def test_gusts_read_the_hour_that_covers_the_arrival():
    assert SERIES.at(1800).gust_mph == 25.0


def test_on_the_hour_uses_that_hour():
    conditions = SERIES.at(3600)
    assert (conditions.wind_mph, conditions.rain_in_hr) == (20.0, 0.3)


def test_times_outside_the_series_are_clamped():
    assert SERIES.at(-500).wind_mph == 10.0
    assert SERIES.at(99_999).wind_mph == 40.0


def test_simplify_drops_collinear_points_and_keeps_corners():
    line = [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]
    assert simplify(line, 0.01) == [(0, 0), (0, 2), (2, 2)]


def test_simplify_leaves_a_two_point_line_alone():
    assert simplify([(0, 0), (1, 1)], 0.01) == [(0, 0), (1, 1)]


def test_simplify_keeps_a_detour_on_a_closed_loop():
    loop = [(0, 0), (1, 0), (0, 0)]
    assert simplify(loop, 0.01) == loop


def test_simplify_handles_a_long_gently_curving_route():
    line = [(index * 0.0001, sin(index / 2000)) for index in range(50_000)]
    simplified = simplify(line, 0.002)
    assert 2 < len(simplified) < 2_000
    assert (simplified[0], simplified[-1]) == (line[0], line[-1])


def test_snapping_coarsens_until_it_fits():
    coordinates = [(40.0, -100.0 + index * 0.12) for index in range(400)]
    assert len(set(snap_to_budget(coordinates, 350))) <= 350


def test_nearby_points_share_one_forecast_cell():
    assert len(set(snap_to_budget([(40.01, -100.01), (40.02, -100.02)], 350))) == 1


def test_finest_grid_is_used_when_it_fits():
    assert build_corridor([[(38.0, -100.0)]], budget=500).step == 0.2


def test_coarsest_checkpoint_grid_is_used_when_nothing_fits():
    coordinates = [(30 + index * 0.7, -120 + index * 0.7) for index in range(30)]
    assert all(float(lat).is_integer() for lat, _ in snap_to_budget(coordinates, 1))


def test_coarsest_corridor_is_used_when_nothing_fits():
    assert build_corridor([[(30.0, -120.0), (45.0, -70.0)]], budget=1).step == 3.0


def test_three_coast_to_coast_routes_fit_the_location_budget():
    paths = [
        [(32.7 + offset + index * 0.0026, -117.2 + index * 0.0097) for index in range(5000)]
        for offset in (0, 4, 8)
    ]
    coordinates = [point for path in paths for point in path[::14]]
    checkpoint_cells = len(set(snap_to_budget(coordinates, 350)))
    corridor = build_corridor(paths, budget=550 - checkpoint_cells)
    assert checkpoint_cells <= 350
    assert checkpoint_cells + len(corridor.cells) <= 550


def test_corridor_cells_sit_at_the_centre_of_their_grid_position():
    corridor = build_corridor([[(38.0, -100.0)]], budget=500)
    for (row, col), (lat, lon) in corridor.cells.items():
        assert lat == pytest.approx(corridor.north - (row + 0.5) * corridor.step)
        assert lon == pytest.approx(corridor.west + (col + 0.5) * corridor.step)


def test_corridor_reaches_its_radius_and_stops():
    centre = (38.0, -100.0)
    corridor = build_corridor([[centre]], budget=500, radius_miles=40)
    miles = [haversine_m(centre, cell) / METERS_PER_MILE for cell in corridor.cells.values()]
    assert 30 < max(miles) < 60


def test_corridor_stays_within_budget_on_a_long_trip():
    path = [(38.0, -120.0 + index * 0.1) for index in range(450)]
    corridor = build_corridor([path], budget=200)
    assert 0 < len(corridor.cells) <= 200
    assert all(0 <= row < corridor.rows for row, _ in corridor.cells)
    assert all(0 <= col < corridor.cols for _, col in corridor.cells)
