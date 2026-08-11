"""Concept normalization to ICD-10-CM, RxNorm, SNOMED CT, and LOINC.

A compact, deterministic lexicon that maps surface mentions (including common
abbreviations and synonyms) to coded concepts. This mirrors the role of
OpenMed's ``clinical/normalization`` layer with a demo-sized vocabulary.
"""

from __future__ import annotations

from .models import Concept

# term (lowercased) -> Concept.  Conditions carry BOTH SNOMED and ICD10; we key
# the primary node on SNOMED and attach ICD10 as an attribute in the graph.
_CONDITIONS: dict[str, tuple[Concept, str]] = {}


def _cond(terms: list[str], snomed: str, snomed_display: str, icd10: str) -> None:
    concept = Concept("SNOMED", snomed, snomed_display)
    for t in terms:
        _CONDITIONS[t.lower()] = (concept, icd10)


_cond(
    ["type 2 diabetes mellitus", "type 2 diabetes", "type ii diabetes", "t2dm",
     "dm2", "dmii", "diabetes mellitus type 2", "diabetes"],
    "44054006", "Type 2 diabetes mellitus", "E11.9",
)
_cond(["hypertension", "htn", "high blood pressure"], "38341003", "Hypertensive disorder", "I10")
_cond(["chronic kidney disease", "ckd", "chronic renal failure"],
      "709044004", "Chronic kidney disease", "N18.9")
_cond(["myocardial infarction", "mi", "heart attack", "acute mi", "stemi", "nstemi"],
      "22298006", "Myocardial infarction", "I21.9")
_cond(["asthma"], "195967001", "Asthma", "J45.909")
_cond(["copd", "chronic obstructive pulmonary disease"],
      "13645005", "Chronic obstructive pulmonary disease", "J44.9")
_cond(["pneumonia"], "233604007", "Pneumonia", "J18.9")
_cond(["atrial fibrillation", "afib", "a-fib", "af"],
      "49436004", "Atrial fibrillation", "I48.91")
_cond(["hyperlipidemia", "high cholesterol", "dyslipidemia"],
      "55822004", "Hyperlipidemia", "E78.5")
_cond(["depression", "major depressive disorder", "mdd"],
      "35489007", "Depressive disorder", "F32.9")
_cond(["obesity", "obese"], "414916001", "Obesity", "E66.9")
_cond(["anemia"], "271737000", "Anemia", "D64.9")

_MEDICATIONS: dict[str, Concept] = {}


def _med(terms: list[str], rxnorm: str, display: str) -> None:
    concept = Concept("RxNorm", rxnorm, display)
    for t in terms:
        _MEDICATIONS[t.lower()] = concept


_med(["metformin", "glucophage"], "6809", "Metformin")
_med(["lisinopril"], "29046", "Lisinopril")
_med(["atorvastatin", "lipitor"], "83367", "Atorvastatin")
_med(["warfarin", "coumadin"], "11289", "Warfarin")
_med(["aspirin", "asa"], "1191", "Aspirin")
_med(["insulin glargine", "lantus"], "274783", "Insulin glargine")
_med(["amlodipine", "norvasc"], "17767", "Amlodipine")
_med(["metoprolol"], "6918", "Metoprolol")
_med(["furosemide", "lasix"], "4603", "Furosemide")
_med(["ibuprofen", "advil", "motrin"], "5640", "Ibuprofen")
_med(["hydrochlorothiazide", "hctz"], "5487", "Hydrochlorothiazide")
_med(["gabapentin", "neurontin"], "25480", "Gabapentin")

_LABS: dict[str, Concept] = {}


def _lab(terms: list[str], loinc: str, display: str) -> None:
    concept = Concept("LOINC", loinc, display)
    for t in terms:
        _LABS[t.lower()] = concept


_lab(["egfr", "estimated gfr", "gfr"], "33914-3", "Estimated glomerular filtration rate")
_lab(["hba1c", "a1c", "hemoglobin a1c", "glycated hemoglobin"], "4548-4", "Hemoglobin A1c")
_lab(["creatinine", "cr", "scr"], "2160-0", "Creatinine")
_lab(["potassium", "k+"], "2823-3", "Potassium")
_lab(["glucose", "blood glucose", "bg"], "2345-7", "Glucose")
_lab(["sodium", "na+"], "2951-2", "Sodium")
_lab(["hemoglobin", "hgb", "hb"], "718-7", "Hemoglobin")
_lab(["ldl", "ldl-c", "ldl cholesterol"], "13457-7", "LDL cholesterol")

_PROCEDURES: dict[str, Concept] = {}


def _proc(terms: list[str], snomed: str, display: str) -> None:
    concept = Concept("SNOMED", snomed, display)
    for t in terms:
        _PROCEDURES[t.lower()] = concept


_proc(["colonoscopy"], "73761001", "Colonoscopy")
_proc(["appendectomy"], "80146002", "Appendectomy")
_proc(["cabg", "coronary artery bypass graft", "coronary bypass"],
      "232717009", "Coronary artery bypass graft")
_proc(["dialysis", "hemodialysis"], "108241001", "Dialysis procedure")


def all_condition_terms() -> list[str]:
    return sorted(_CONDITIONS.keys(), key=len, reverse=True)


def all_medication_terms() -> list[str]:
    return sorted(_MEDICATIONS.keys(), key=len, reverse=True)


def all_lab_terms() -> list[str]:
    return sorted(_LABS.keys(), key=len, reverse=True)


def all_procedure_terms() -> list[str]:
    return sorted(_PROCEDURES.keys(), key=len, reverse=True)


def normalize_condition(term: str) -> tuple[Concept | None, str | None]:
    hit = _CONDITIONS.get(term.lower())
    if hit is None:
        return None, None
    return hit[0], hit[1]


def normalize_medication(term: str) -> Concept | None:
    return _MEDICATIONS.get(term.lower())


def normalize_lab(term: str) -> Concept | None:
    return _LABS.get(term.lower())


def normalize_procedure(term: str) -> Concept | None:
    return _PROCEDURES.get(term.lower())
