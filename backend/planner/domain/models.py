from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float


@dataclass(frozen=True)
class RoutePath:
    points: list[tuple[float, float]]
    distance_m: list[float]
    time_s: list[float]

    @property
    def length_m(self):
        return self.distance_m[-1]

    @property
    def duration_s(self):
        return self.time_s[-1]

    def locate(self, distance_m):
        if distance_m <= 0:
            return (*self.points[0], self.time_s[0])
        if distance_m >= self.length_m:
            return (*self.points[-1], self.time_s[-1])
        index = bisect_right(self.distance_m, distance_m) - 1
        span = self.distance_m[index + 1] - self.distance_m[index]
        fraction = (distance_m - self.distance_m[index]) / span
        start, end = self.points[index], self.points[index + 1]
        lat = start[0] + (end[0] - start[0]) * fraction
        lon = start[1] + (end[1] - start[1]) * fraction
        time_s = self.time_s[index] + (self.time_s[index + 1] - self.time_s[index]) * fraction
        return lat, lon, time_s

    def slice(self, from_m, to_m):
        start = self.locate(from_m)
        end = self.locate(to_m)
        first = bisect_right(self.distance_m, from_m)
        last = bisect_left(self.distance_m, to_m)
        return [start[:2], *self.points[first:last], end[:2]]


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    lat: float
    lon: float
    eta: datetime
    covered_miles: float
    from_m: float
    to_m: float


@dataclass(frozen=True)
class Conditions:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
