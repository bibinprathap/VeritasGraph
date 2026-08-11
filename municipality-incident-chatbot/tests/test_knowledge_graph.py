"""Knowledge-graph (VeritasGraph) classification + routing tests."""

import pytest


@pytest.mark.parametrize(
    "text,expected",
    [
        ("the trash is overflowing near the market", "trash_overflow"),
        ("there's an abandoned car dumped for weeks", "abandoned_vehicle"),
        ("too many people gathering, dangerous crowd", "overcrowding"),
        ("a car is parked illegally blocking the road", "illegal_parking"),
        ("i want to complain about the weather forecast", None),
    ],
)
def test_classify(kg, text, expected):
    assert kg.classify(text) == expected


def test_route_resolves_department_and_sla(kg):
    route = kg.route("trash_overflow")
    assert route is not None
    assert route["department"]["name"] == "Sanitation Department"
    assert route["sla"]["response_hours"] == 24
    assert route["sla"]["priority"] == "high"
    # Genuine multi-hop retrieval produced a reasoning path over the graph.
    assert route["reasoning_path"]
    assert "Solid Waste Management Policy" in route["policies"]


def test_route_uses_veritasgraph_retrieval(kg):
    # Each incident type routes to a distinct department via the graph.
    assert kg.route("illegal_parking")["department"]["name"] == "Traffic Police"
    assert kg.route("overcrowding")["department"]["name"] == "Public Safety Department"
    assert kg.route("abandoned_vehicle")["department"]["name"] == "Transport Department"


def test_incident_metadata(kg):
    inc = kg.incident("trash_overflow")
    assert inc["label"] == "Trash Overflow"
    assert "garbage" in inc["cv_labels"]
