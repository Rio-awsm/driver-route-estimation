from dataclasses import dataclass
from math import ceil, floor

from .models import Conditions


@dataclass(frozen=True)
class HourlySeries:
    times: list[int]
    wind_mph: list[float]
    gust_mph: list[float]
    rain_in: list[float]
    snow_in: list[float]

    def at(self, epoch_s):
        # Wind is instantaneous; gusts, rain and snow cover the preceding hour.
        position = (epoch_s - self.times[0]) / 3600
        position = min(max(position, 0.0), len(self.times) - 1)
        lower, upper = floor(position), ceil(position)
        fraction = position - lower
        wind = self.wind_mph[lower] + (self.wind_mph[upper] - self.wind_mph[lower]) * fraction
        return Conditions(
            wind_mph=wind,
            gust_mph=self.gust_mph[upper],
            rain_in_hr=self.rain_in[upper],
            snow_in_hr=self.snow_in[upper],
        )
