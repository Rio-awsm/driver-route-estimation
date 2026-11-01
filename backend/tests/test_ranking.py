from planner.domain.ranking import RouteScore, explain, rank_routes, score_route
from planner.domain.risk import Risk


def make_score(route_id, no_travel=0, severe=0, high=0, average=0.0, duration=3600):
    return RouteScore(route_id, no_travel, severe, high, average, duration)


def winner(*scores):
    return rank_routes(scores)[0].route_id


def test_any_no_travel_loses_to_a_route_with_more_severe_miles():
    assert winner(make_score("A", no_travel=1), make_score("B", severe=500)) == "B"


def test_fewest_severe_miles_comes_first():
    assert winner(make_score("A", severe=5), make_score("B", severe=2, high=400)) == "B"


def test_high_miles_break_a_severe_tie():
    assert winner(make_score("A", severe=2, high=9), make_score("B", severe=2, high=3)) == "B"


def test_average_risk_breaks_a_high_tie():
    assert winner(make_score("A", average=1.2), make_score("B", average=0.4)) == "B"


def test_travel_time_is_the_last_tie_break():
    assert winner(make_score("A", duration=9000), make_score("B", duration=7000)) == "B"


def test_average_risk_is_weighted_by_miles():
    score = score_route("A", [(90, Risk.LOW), (10, Risk.NO_TRAVEL)], 100)
    assert score.average_risk == 0.4
    assert score.no_travel_miles == 10


def test_explain_blocks_when_every_route_has_no_travel():
    ranked = rank_routes([make_score("A", no_travel=9), make_score("B", no_travel=4)])
    assert explain(ranked).startswith("Do not depart")


def test_explain_names_the_deciding_criterion():
    ranked = rank_routes([make_score("A", severe=12), make_score("B", severe=3)])
    assert "Severe miles: 3 vs 12 on Route A" in explain(ranked)


def test_explain_only_claims_what_it_compared():
    ranked = rank_routes(
        [
            make_score("A", high=5),
            make_score("B", high=9),
            make_score("C", severe=3, high=0),
        ]
    )
    assert explain(ranked) == "Route A wins on High miles: 5 vs 9 on Route B."


def test_explain_shows_a_short_no_travel_stretch():
    ranked = rank_routes([make_score("A", no_travel=0.4), make_score("B", no_travel=9)])
    assert "(0.4 mi)" in explain(ranked)


def test_explain_handles_a_single_route():
    assert explain([make_score("A")]) == "Route A is the only route available."


def test_explain_says_when_time_decided():
    ranked = rank_routes([make_score("A", duration=9000), make_score("B", duration=7000)])
    assert "wins on travel time" in explain(ranked)
