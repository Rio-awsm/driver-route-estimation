import time

import httpx
from django.conf import settings
from django.core.cache import cache

from ..domain.weather import HourlySeries
from ..exceptions import UpstreamError, WeatherRateLimited

BATCH_SIZE = 200
CACHE_SECONDS = 30 * 60
RATE_LIMIT_WAIT_SECONDS = 30
RATE_LIMIT_RETRIES = 2
HOURLY_VARIABLES = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
TIME_FORMAT = "%Y-%m-%dT%H:%M"


def _clean(values):
    return [value or 0.0 for value in values]


def parse_series(location):
    hourly = location["hourly"]
    rain = _clean(hourly["rain"])
    showers = _clean(hourly["showers"])
    return HourlySeries(
        times=hourly["time"],
        wind_mph=_clean(hourly["wind_speed_10m"]),
        gust_mph=_clean(hourly["wind_gusts_10m"]),
        # precipitation also includes snow.
        rain_in=[a + b for a, b in zip(rain, showers)],
        snow_in=_clean(hourly["snowfall"]),
    )


def _post_batch(cells, start, end):
    data = {
        "latitude": ",".join(str(lat) for lat, _ in cells),
        "longitude": ",".join(str(lon) for _, lon in cells),
        "hourly": HOURLY_VARIABLES,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "timeformat": "unixtime",
        "cell_selection": "nearest",
        "start_hour": start.strftime(TIME_FORMAT),
        "end_hour": end.strftime(TIME_FORMAT),
    }
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            response = httpx.post(settings.OPEN_METEO_URL, data=data, timeout=60.0)
        except httpx.HTTPError as error:
            raise UpstreamError("The weather provider could not be reached.") from error
        if response.status_code != 429:
            break
        if attempt < RATE_LIMIT_RETRIES:
            time.sleep(RATE_LIMIT_WAIT_SECONDS)
    if response.status_code == 429:
        raise WeatherRateLimited()
    if response.status_code != 200:
        raise UpstreamError(f"The weather provider returned {response.status_code}.")
    body = response.json()
    return body if isinstance(body, list) else [body]


def _cache_key(cell, start, end):
    return f"wx:{cell[0]}:{cell[1]}:{start:%Y%m%d%H}:{end:%Y%m%d%H}"


def fetch_series(cells, start, end):
    cells = sorted(set(cells))
    keys = {_cache_key(cell, start, end): cell for cell in cells}
    cached = cache.get_many(keys)
    series = {keys[key]: value for key, value in cached.items()}
    missing = [cell for cell in cells if cell not in series]

    for offset in range(0, len(missing), BATCH_SIZE):
        batch = missing[offset : offset + BATCH_SIZE]
        fresh = dict(zip(batch, map(parse_series, _post_batch(batch, start, end))))
        cache.set_many(
            {_cache_key(cell, start, end): value for cell, value in fresh.items()},
            CACHE_SECONDS,
        )
        series.update(fresh)
    return series
