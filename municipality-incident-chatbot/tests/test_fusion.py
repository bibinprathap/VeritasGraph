"""Evidence-fusion scoring tests."""

from app import config
from app.cv_service import Detection
from app.external_sources import Corroboration
from app.fusion import fuse


def test_full_evidence_auto_validates():
    result = fuse(
        "trash_overflow",
        ["garbage"],
        [Detection("garbage", 0.9)],
        vlm_confidence=0.88,
        location={"lat": 25.2, "lon": 55.3, "zone": "downtown"},
        corroboration=Corroboration(cctv_confidence=0.87, sensor_signal=0.96),
    )
    assert result.outcome == config.Outcome.AUTO_VALIDATED
    assert result.score >= config.THRESHOLD_AUTO


def test_photo_only_needs_review_and_is_capped():
    result = fuse(
        "trash_overflow",
        ["garbage"],
        [Detection("garbage", 0.9)],
        vlm_confidence=0.9,
        location={"zone": "suburb"},
        corroboration=Corroboration(),  # nothing corroborated
    )
    assert result.outcome == config.Outcome.NEEDS_REVIEW
    assert result.score <= config.CAP_NO_CORROBORATION


def test_no_evidence_rejected():
    result = fuse(
        "trash_overflow",
        ["garbage"],
        [],
        vlm_confidence=0.2,
        location={"zone": "suburb"},
        corroboration=Corroboration(),
    )
    assert result.outcome == config.Outcome.REJECTED
