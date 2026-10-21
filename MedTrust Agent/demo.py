"""End-to-end reference demo (no network, no models).

Run (from the Awesome-AI4Med directory):
    /home/sijo/VeritasGraph/.venv/bin/python -m medtrust.demo
"""

from __future__ import annotations

from medtrust import MedTrustAgent
from medtrust.iam import User, Action


def main() -> None:
    agent = MedTrustAgent()

    clinician = User("u-alice", role="clinician", team="endocrinology")
    analyst = User("u-bob", role="safety_analyst", team="pv")
    guest = User("u-carol", role="guest")

    print("== 1. Clinician literature query (approved) ==")
    r = agent.handle(clinician, "What is first-line therapy for diabetes and metformin eGFR limits?")
    print(r.approved, r.citations, "audit:", r.audit_id[:12])
    print(r.answer)

    print("\n== 2. Guest tries adverse-event query (denied: least privilege) ==")
    r = agent.handle(guest, "Show adverse event reports for metformin")
    print(r.approved, "reason:", r.reason)

    print("\n== 3. Analyst export without step-up (denied, escalated) ==")
    r = agent.handle(analyst, "export patient data for cohort")
    print(r.approved, "escalated:", r.escalated, "reason:", r.reason)

    print("\n== 4. Analyst export WITH step-up (approved) ==")
    agent.iam.grant_step_up(analyst, Action.EXPORT_PATIENT_DATA)
    r = agent.handle(analyst, "export patient data for cohort P001")
    print(r.approved, "reason:", r.reason)

    print("\n== Observability ==")
    print("counters:", agent.obs.counters)
    print("audit chain valid:", agent.governance.audit.verify())


if __name__ == "__main__":
    main()
