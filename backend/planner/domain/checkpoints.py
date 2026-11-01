from datetime import timedelta
from math import ceil

from .geo import METERS_PER_MILE
from .models import Checkpoint

MIN_LAST_STRETCH_M = 0.25 * METERS_PER_MILE


def _distances(length_m, step_m):
    distances = [index * step_m for index in range(ceil(length_m / step_m))]
    if len(distances) > 1 and length_m - distances[-1] < MIN_LAST_STRETCH_M:
        distances.pop()
    return [*distances, length_m]


def sample_checkpoints(route, interval_miles, departure):
    distances = _distances(route.length_m, interval_miles * METERS_PER_MILE)

    cuts = [0.0]
    cuts += [(left + right) / 2 for left, right in zip(distances, distances[1:])]
    cuts.append(route.length_m)

    checkpoints = []
    for index, distance in enumerate(distances):
        lat, lon, time_s = route.locate(distance)
        from_m, to_m = cuts[index], cuts[index + 1]
        checkpoints.append(
            Checkpoint(
                mile=distance / METERS_PER_MILE,
                lat=lat,
                lon=lon,
                eta=departure + timedelta(seconds=time_s),
                covered_miles=(to_m - from_m) / METERS_PER_MILE,
                from_m=from_m,
                to_m=to_m,
            )
        )
    return checkpoints
