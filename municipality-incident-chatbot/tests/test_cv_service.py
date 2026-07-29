"""Computer-vision service tests (simulated backend)."""

from app.cv_service import Detection, SimulatedBackend, VisionService


def test_sidecar_detections(make_photo):
    path = make_photo("report.jpg", [{"label": "garbage", "confidence": 0.92}])
    svc = VisionService(backend=SimulatedBackend())
    dets = svc.analyze(path, ["garbage", "trash_bag"])
    assert len(dets) == 1
    assert dets[0].label == "garbage"
    assert dets[0].confidence == 0.92


def test_filename_token_detection(tmp_path):
    img = tmp_path / "car_on_curb.jpg"
    img.write_bytes(b"fake")
    svc = VisionService(backend=SimulatedBackend())
    dets = svc.analyze(str(img), ["car", "truck"])
    assert any(d.label == "car" for d in dets)


def test_missing_image_returns_no_detections():
    svc = VisionService(backend=SimulatedBackend())
    assert svc.analyze("/does/not/exist.jpg", ["car"]) == []


def test_verify_claim_confidence():
    svc = VisionService(backend=SimulatedBackend())
    match = [Detection("garbage", 0.9)]
    assert svc.verify_claim("x", "Trash Overflow", match, ["garbage"]) > 0.8
    assert svc.verify_claim("x", "Trash Overflow", [], ["garbage"]) < 0.3
