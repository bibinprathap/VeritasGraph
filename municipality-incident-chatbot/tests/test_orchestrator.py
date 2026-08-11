"""End-to-end orchestrator tests covering every validation outcome."""

from app import config


def test_auto_validated_creates_case(chatbot, make_photo):
    photo = make_photo("garbage.jpg", [{"label": "garbage", "confidence": 0.9}])
    result = chatbot.handle_report(
        "the trash is overflowing here", image_path=photo,
        location={"zone": "downtown"},
    )
    assert result.outcome == config.Outcome.AUTO_VALIDATED
    assert result.case_id and result.case_id.startswith("MUN-")
    assert result.department == "Sanitation Department"
    assert result.sla_hours == 24
    assert chatbot.cases.get(result.case_id) is not None


def test_needs_review_when_no_corroboration(chatbot, make_photo):
    photo = make_photo("garbage2.jpg", [{"label": "garbage", "confidence": 0.9}])
    result = chatbot.handle_report(
        "trash overflowing", image_path=photo, location={"zone": "far-suburb"},
    )
    assert result.outcome == config.Outcome.NEEDS_REVIEW
    assert result.case_id is not None


def test_rejected_without_evidence(chatbot):
    result = chatbot.handle_report(
        "trash overflowing", image_path=None, location={"zone": "far-suburb"},
    )
    assert result.outcome == config.Outcome.REJECTED
    assert result.case_id is None


def test_out_of_scope_rejected(chatbot):
    result = chatbot.handle_report("please fix my electricity bill dispute")
    assert result.outcome == config.Outcome.REJECTED
    assert result.incident_code is None


def test_duplicate_detection(chatbot, make_photo):
    photo = make_photo("garbage3.jpg", [{"label": "garbage", "confidence": 0.9}])
    first = chatbot.handle_report(
        "trash overflowing", image_path=photo, location={"zone": "downtown"},
    )
    assert first.outcome == config.Outcome.AUTO_VALIDATED

    photo2 = make_photo("garbage4.jpg", [{"label": "garbage", "confidence": 0.9}])
    second = chatbot.handle_report(
        "garbage still overflowing here", image_path=photo2,
        location={"zone": "downtown"},
    )
    assert second.duplicate_of == first.case_id
    assert second.outcome == config.Outcome.REJECTED


def test_illegal_parking_routes_to_traffic(chatbot, make_photo):
    photo = make_photo("car_blocking.jpg", [{"label": "car", "confidence": 0.88}])
    result = chatbot.handle_report(
        "a car is parked illegally blocking the road",
        image_path=photo, location={"zone": "downtown"},
    )
    assert result.incident_code == "illegal_parking"
    assert result.department == "Traffic Police"
