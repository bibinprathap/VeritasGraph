"""Synthetic clinical notes for demos and tests.

All content is fabricated. No real PHI. Names/dates/IDs are fake so the
de-identification stage has something to redact.
"""

from __future__ import annotations

from .models import Document

SAMPLE_DOCUMENTS: list[Document] = [
    Document(
        doc_id="note-001",
        patient_id="P001",
        encounter_date="2025-03-14",
        encounter_type="discharge_summary",
        text="""Patient: John A Smith    MRN: 4483920
Date of Service: 03/14/2025    Phone: (617) 555-0142

HPI: Patient denies any history of diabetes. Reports fatigue for two weeks.

Problem List:
1. Type 2 diabetes mellitus, on metformin 500mg BID.
2. Hypertension, well controlled on lisinopril 10mg daily.

Labs: eGFR 24 mL/min. HbA1c 8.1%. Creatinine 2.4 mg/dL. Potassium 4.5.

Assessment and Plan: Type 2 diabetes mellitus with diabetic nephropathy.
Continue metformin. Recheck eGFR in 2 weeks.
""",
    ),
    Document(
        doc_id="note-002",
        patient_id="P002",
        encounter_date="2025-04-02",
        encounter_type="progress_note",
        text="""Patient: Maria Gonzalez    MRN: 7781234
Contact: maria.g@example.com    DOB: 07/22/1961

HPI: Type 2 diabetes, poorly controlled. Takes metformin 1000mg BID.

Family History: Father with myocardial infarction. Mother with breast cancer.

Labs: eGFR 68 mL/min. HbA1c 9.4%. LDL 142 mg/dL.

Assessment: Type 2 diabetes mellitus, hyperlipidemia. Start atorvastatin 40mg daily.
""",
    ),
    Document(
        doc_id="note-003",
        patient_id="P003",
        encounter_date="2025-02-19",
        encounter_type="progress_note",
        text="""Patient: Robert Lee    MRN: 5567001

HPI: History of atrial fibrillation on warfarin. No evidence of diabetes.

Problem List:
1. Atrial fibrillation.
2. Hypertension on amlodipine 5mg daily.

Labs: eGFR 55 mL/min. Potassium 4.1. Creatinine 1.3 mg/dL.

Assessment and Plan: Continue warfarin for atrial fibrillation. Rule out CKD.
""",
    ),
    Document(
        doc_id="note-004",
        patient_id="P004",
        encounter_date="2025-05-30",
        encounter_type="discharge_summary",
        text="""Patient: Aisha Khan    MRN: 9902388    SSN: 123-45-6789

HPI: Type 2 diabetes mellitus with worsening renal function. On metformin 500mg BID
and insulin glargine 20 units qhs.

Labs: eGFR 22 mL/min. HbA1c 7.6%. Creatinine 2.8 mg/dL.

Assessment and Plan: Type 2 diabetes mellitus, chronic kidney disease stage 4.
Hold metformin given eGFR < 30. Continue insulin glargine.
""",
    ),
]
