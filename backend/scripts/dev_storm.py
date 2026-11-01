# Local only: fakes a 50 mph storm north of 42N for 24 hours. Never deploy.
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.management import call_command

from planner.clients import open_meteo
from planner.domain.weather import HourlySeries

STORM_NORTH_OF = 42.0
STORM_HOURS = 24


def stormy_forecast(cells, start, end):
    hours = int((end - start).total_seconds() // 3600) + 1
    times = [int(start.timestamp()) + hour * 3600 for hour in range(hours)]
    calm, storm = [5.0] * hours, [50.0 if hour < STORM_HOURS else 5.0 for hour in range(hours)]
    dry = [0.0] * hours
    return {
        cell: HourlySeries(times, storm if cell[0] >= STORM_NORTH_OF else calm, calm, dry, dry)
        for cell in set(cells)
    }


open_meteo.fetch_series = stormy_forecast
call_command("runserver", "8000", "--noreload")
