from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView

from .clients import tomtom
from .domain.models import Place
from .serializers import PlanRequestSerializer
from .services.plan import build_plan

GEOCODE_CACHE_SECONDS = 24 * 60 * 60
MIN_GEOCODE_CHARS = 2


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class GeocodeView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < MIN_GEOCODE_CHARS:
            return Response({"results": []})
        key = f"geocode:{query.lower()[:100].replace(' ', '_')}"
        results = cache.get(key)
        if results is None:
            results = tomtom.search_places(query)
            cache.set(key, results, GEOCODE_CACHE_SECONDS)
        return Response({"results": results})


class PlanView(APIView):
    def post(self, request):
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        plan = build_plan(
            origin=Place(**data["origin"]),
            destination=Place(**data["destination"]),
            departure=data["departure"],
            load_lb=data["load_lb"],
            interval_miles=data["interval_miles"],
        )
        return Response(plan)
