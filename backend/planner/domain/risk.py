from enum import IntEnum

LOAD_NO_TRAVEL_LB = 30_000
LOAD_SEVERE_LB = 40_000


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self):
        return self.name.replace("_", " ").title()


def classify_wind(mph, load_lb):
    if mph >= 55:
        return Risk.NO_TRAVEL
    if mph >= 45:
        return Risk.NO_TRAVEL if load_lb > LOAD_NO_TRAVEL_LB else Risk.SEVERE
    if mph >= 35:
        return Risk.SEVERE if load_lb > LOAD_SEVERE_LB else Risk.HIGH
    if mph >= 25:
        return Risk.MODERATE
    return Risk.LOW


def classify_rain(inches_per_hour):
    if inches_per_hour > 1.00:
        return Risk.NO_TRAVEL
    if inches_per_hour >= 0.50:
        return Risk.SEVERE
    if inches_per_hour >= 0.25:
        return Risk.HIGH
    if inches_per_hour >= 0.10:
        return Risk.MODERATE
    return Risk.LOW


def classify_snow(inches_per_hour):
    if inches_per_hour > 3.0:
        return Risk.NO_TRAVEL
    if inches_per_hour >= 2.0:
        return Risk.SEVERE
    if inches_per_hour >= 1.0:
        return Risk.HIGH
    if inches_per_hour >= 0.5:
        return Risk.MODERATE
    return Risk.LOW


def classify(wind_mph, rain_in_hr, snow_in_hr, load_lb):
    levels = {
        "wind": classify_wind(wind_mph, load_lb),
        "rain": classify_rain(rain_in_hr),
        "snow": classify_snow(snow_in_hr),
    }
    driver = max(levels, key=levels.get)
    return levels[driver], driver
