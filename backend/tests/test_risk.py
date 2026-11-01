import pytest

from planner.domain.risk import Risk, classify, classify_rain, classify_snow, classify_wind

LIGHT = 20_000


@pytest.mark.parametrize(
    "mph, expected",
    [
        (0, Risk.LOW),
        (24.9, Risk.LOW),
        (25, Risk.MODERATE),
        (34.9, Risk.MODERATE),
        (35, Risk.HIGH),
        (44.9, Risk.HIGH),
        (45, Risk.SEVERE),
        (54.9, Risk.SEVERE),
        (55, Risk.NO_TRAVEL),
        (80, Risk.NO_TRAVEL),
    ],
)
def test_wind_bands_for_light_load(mph, expected):
    assert classify_wind(mph, LIGHT) == expected


@pytest.mark.parametrize(
    "mph, load, expected",
    [
        (55, 0, Risk.NO_TRAVEL),
        (50, 30_000, Risk.SEVERE),
        (50, 30_001, Risk.NO_TRAVEL),
        (40, 40_000, Risk.HIGH),
        (40, 40_001, Risk.SEVERE),
        (30, 80_000, Risk.MODERATE),
    ],
)
def test_load_rules(mph, load, expected):
    assert classify_wind(mph, load) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [
        (0.09, Risk.LOW),
        (0.10, Risk.MODERATE),
        (0.24, Risk.MODERATE),
        (0.25, Risk.HIGH),
        (0.49, Risk.HIGH),
        (0.50, Risk.SEVERE),
        (1.00, Risk.SEVERE),
        (1.01, Risk.NO_TRAVEL),
    ],
)
def test_rain_bands(rate, expected):
    assert classify_rain(rate) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [
        (0.49, Risk.LOW),
        (0.5, Risk.MODERATE),
        (0.99, Risk.MODERATE),
        (1.0, Risk.HIGH),
        (1.99, Risk.HIGH),
        (2.0, Risk.SEVERE),
        (3.0, Risk.SEVERE),
        (3.01, Risk.NO_TRAVEL),
    ],
)
def test_snow_bands(rate, expected):
    assert classify_snow(rate) == expected


def test_checkpoint_takes_the_worst_condition():
    assert classify(10, 0.3, 2.5, LIGHT) == (Risk.SEVERE, "snow")


def test_load_rule_flows_through_overall_classification():
    assert classify(50, 0, 0, 35_000) == (Risk.NO_TRAVEL, "wind")


def test_labels_read_like_the_spec():
    assert Risk.NO_TRAVEL.label == "No Travel"
