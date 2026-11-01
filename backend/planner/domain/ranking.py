from dataclasses import dataclass

from .risk import Risk


@dataclass(frozen=True)
class RouteScore:
    route_id: str
    no_travel_miles: float
    severe_miles: float
    high_miles: float
    average_risk: float
    duration_s: float

    @property
    def sort_key(self):
        # Not in the spec's list, but a forbidden route must never win.
        return (
            round(self.no_travel_miles, 1),
            round(self.severe_miles, 1),
            round(self.high_miles, 1),
            round(self.average_risk, 2),
            self.duration_s,
        )


def score_route(route_id, stretches, duration_s):
    miles_at = {level: 0.0 for level in Risk}
    for miles, level in stretches:
        miles_at[level] += miles
    total = sum(miles_at.values())
    weighted = sum(miles * level for miles, level in stretches)
    return RouteScore(
        route_id=route_id,
        no_travel_miles=miles_at[Risk.NO_TRAVEL],
        severe_miles=miles_at[Risk.SEVERE],
        high_miles=miles_at[Risk.HIGH],
        average_risk=weighted / total if total else 0.0,
        duration_s=duration_s,
    )


def rank_routes(scores):
    return sorted(scores, key=lambda score: score.sort_key)


def explain(ranked):
    best = ranked[0]
    if best.no_travel_miles > 0:
        return (
            f"Do not depart: every route crosses No Travel conditions. Route {best.route_id} "
            f"has the fewest ({best.sort_key[0]:g} mi). Try a later departure."
        )
    if len(ranked) == 1:
        return f"Route {best.route_id} is the only route available."
    fastest = min(ranked, key=lambda score: score.duration_s)
    other = fastest if fastest is not best else ranked[1]
    rival = "the faster Route" if other is fastest else "Route"
    criteria = ("No Travel miles", "Severe miles", "High miles", "average risk")
    for name, mine, theirs in zip(criteria, best.sort_key, other.sort_key):
        if mine < theirs:
            return (
                f"Route {best.route_id} wins on {name}: "
                f"{mine:g} vs {theirs:g} on {rival} {other.route_id}."
            )
    return f"Routes tie on weather risk, so Route {best.route_id} wins on travel time."
