from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344
MILES_PER_DEGREE_LAT = 69.0


def haversine_m(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(h))


def _offset_from_chord(point, start, end):
    dx, dy = end[1] - start[1], end[0] - start[0]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return abs(point[1] - start[1]) + abs(point[0] - start[0])
    return abs(dy * (point[1] - start[1]) - dx * (point[0] - start[0])) / sqrt(length_squared)


def simplify(points, tolerance_deg):
    if len(points) < 3:
        return list(points)
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        farthest, max_offset = None, tolerance_deg
        for index in range(first + 1, last):
            offset = _offset_from_chord(points[index], points[first], points[last])
            if offset > max_offset:
                farthest, max_offset = index, offset
        if farthest is not None:
            keep.add(farthest)
            stack.extend([(first, farthest), (farthest, last)])
    return [points[index] for index in sorted(keep)]
