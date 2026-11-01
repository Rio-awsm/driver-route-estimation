from rest_framework.exceptions import APIException


class UpstreamError(APIException):
    status_code = 502
    default_detail = "A map or weather provider failed. Please try again."
    default_code = "upstream_error"


class WeatherRateLimited(APIException):
    status_code = 503
    default_detail = "The weather provider is busy. Please try again in a minute."
    default_code = "weather_rate_limited"


class NoRouteFound(APIException):
    status_code = 422
    default_detail = "No truck route was found between these places."
    default_code = "no_route_found"
