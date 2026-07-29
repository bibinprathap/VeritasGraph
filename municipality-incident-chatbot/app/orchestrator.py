"""Chatbot orchestrator (Orchestration Layer).

Ties the channel-agnostic conversation to the knowledge graph, CV validation,
evidence fusion and case registration — implementing the end-to-end sequence in
``01_architecture.md`` §3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import config
from .case_service import CaseService
from .cv_service import VisionService
from .exif_utils import extract_geo
from .external_sources import ExternalSources
from .fusion import fuse
from .knowledge_graph import MunicipalKnowledgeGraph


@dataclass
class ReportResult:
    message: str
    outcome: str
    incident_code: Optional[str] = None
    department: Optional[str] = None
    sla_hours: Optional[int] = None
    validation_score: Optional[float] = None
    case_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    reasoning_path: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    reporter: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__


class IncidentChatbot:
    """The single 'brain' shared by every channel (web / WhatsApp / mobile)."""

    def __init__(
        self,
        kg: Optional[MunicipalKnowledgeGraph] = None,
        vision: Optional[VisionService] = None,
        external: Optional[ExternalSources] = None,
        cases: Optional[CaseService] = None,
    ) -> None:
        self.kg = kg or MunicipalKnowledgeGraph()
        self.vision = vision or VisionService()
        self.external = external or ExternalSources()
        self.cases = cases or CaseService()

    # ------------------------------------------------------------------ #
    def handle_report(
        self,
        text: str,
        image_path: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        reporter: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous",
    ) -> ReportResult:
        # Normalise reporter contact details (name / phone / email).
        reporter = {
            k: v for k, v in (reporter or {}).items() if v not in (None, "")
        }

        # 1) Classify + ground via the VeritasGraph knowledge graph.
        code = self.kg.classify(text)
        if code is None:
            return ReportResult(
                message=(
                    "I couldn't match your report to a municipal service I handle "
                    "(trash overflow, abandoned vehicle, overcrowding, illegal parking). "
                    "Could you describe the problem differently?"
                ),
                outcome=config.Outcome.REJECTED,
                reasons=["Out of scope: no matching incident category."],
            )

        route = self.kg.route(code)
        incident = route["incident"]
        dept = route["department"]
        sla = route["sla"]

        # 2) Resolve location: merge citizen-provided location with photo EXIF.
        location = dict(location or {})
        if image_path:
            geo = extract_geo(image_path)
            location.setdefault("lat", geo.get("lat"))
            location.setdefault("lon", geo.get("lon"))
            if location.get("lat") is None:
                location.pop("lat", None)
            if location.get("lon") is None:
                location.pop("lon", None)

        # 3) Computer-vision validation (detect + verify the claim).
        detections = self.vision.analyze(image_path or "", incident["cv_labels"])
        vlm_conf = self.vision.verify_claim(
            image_path or "", incident["label"], detections, incident["cv_labels"]
        )

        # 4) External corroboration (CCTV / sensors) — optional.
        corroboration = self.external.fetch(code, location or None)

        # 5) Duplicate / jurisdiction check.
        duplicate = self.cases.find_duplicate(code, location or None)
        if duplicate is not None:
            return ReportResult(
                message=(
                    f"❌ This looks like a duplicate of case **{duplicate['id']}** already "
                    f"logged for {incident['label']} at this location. We've linked your "
                    f"report to it; the {dept['name']} is already on it."
                ),
                outcome=config.Outcome.REJECTED,
                incident_code=code,
                department=dept["name"],
                sla_hours=sla["response_hours"],
                duplicate_of=duplicate["id"],
                reasons=["Duplicate of an existing open case."],
                reasoning_path=route["reasoning_path"],
            )

        # 6) Fuse evidence into a validation score + outcome.
        fusion = fuse(
            code,
            incident["cv_labels"],
            detections,
            vlm_conf,
            location or None,
            corroboration,
            vlm_available=self.vision.vlm_available,
        )

        evidence = {
            "detections": [d.as_dict() for d in detections],
            "vlm_confidence": round(vlm_conf, 4),
            "signals": fusion.signals,
            "corroboration": corroboration.details,
            "location": location or None,
        }

        # 7) Register the case per outcome.
        grounded = self.kg.grounded_reply(route)
        if fusion.outcome == config.Outcome.REJECTED:
            return ReportResult(
                message=(
                    f"{grounded}\n\n❌ I could not validate this report "
                    f"(confidence {fusion.score:.2f}). "
                    "Please resend a clearer photo showing the problem, or add the "
                    "exact location so an officer can look into it."
                ),
                outcome=fusion.outcome,
                incident_code=code,
                department=dept["name"],
                sla_hours=sla["response_hours"],
                validation_score=fusion.score,
                reasons=fusion.reasons,
                reasoning_path=route["reasoning_path"],
                evidence=evidence,
            )

        case = self.cases.register(
            incident_code=code,
            department=dept["name"],
            location=location or None,
            outcome=fusion.outcome,
            validation_score=fusion.score,
            evidence=evidence,
            reporter=reporter or None,
        )

        contact_line = ""
        if reporter.get("name"):
            who = reporter["name"]
            how = reporter.get("phone") or reporter.get("email")
            contact_line = (
                f"\n\nThanks {who} — we'll contact you"
                + (f" on {how}" if how else "")
                + " with any updates."
            )

        if fusion.outcome == config.Outcome.AUTO_VALIDATED:
            msg = (
                f"{grounded}\n\n✅ Case **{case['id']}** registered and routed to the "
                f"{dept['name']}. Expected response within {sla['response_hours']}h "
                f"(validation score {fusion.score:.2f}).{contact_line}"
            )
        else:  # NEEDS_REVIEW
            msg = (
                f"{grounded}\n\n🟡 Case **{case['id']}** logged (validation score "
                f"{fusion.score:.2f}). An officer will verify the evidence shortly "
                f"before dispatch.{contact_line}"
            )

        return ReportResult(
            message=msg,
            outcome=fusion.outcome,
            incident_code=code,
            department=dept["name"],
            sla_hours=sla["response_hours"],
            validation_score=fusion.score,
            case_id=case["id"],
            reasons=fusion.reasons,
            reasoning_path=route["reasoning_path"],
            evidence=evidence,
            reporter=reporter,
        )
