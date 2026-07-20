"""Drug enrichment layer: drug-drug interactions (DDI) and side effects.

A compact, deterministic reference dataset shaped like the records produced by
CKG's ``drugBankParser`` (interactions) and ``siderParser`` (side effects),
keyed on the same RxNorm codes emitted by :mod:`clinical_kg.normalize`. This
mirrors how a real deployment would load the customer's own licensed DrugBank /
SIDER extracts -- the graph and query layers stay unchanged.

All records here are well-known, clinically documented interactions encoded for
demonstration. In production these tables are populated from licensed sources.
"""

from __future__ import annotations

from dataclasses import dataclass

# Severity ranking (higher = more serious), mirrors DrugBank/label conventions.
SEVERITY_RANK: dict[str, int] = {
    "minor": 1,
    "moderate": 2,
    "major": 3,
    "contraindicated": 4,
}


@dataclass(frozen=True)
class DrugInteraction:
    """A single drug-drug interaction between two RxNorm-coded medications."""

    rxnorm_a: str
    display_a: str
    rxnorm_b: str
    display_b: str
    severity: str  # minor | moderate | major | contraindicated
    description: str
    source: str = "DrugBank (reference)"

    def pair_key(self) -> frozenset[str]:
        return frozenset({self.rxnorm_a, self.rxnorm_b})

    def rank(self) -> int:
        return SEVERITY_RANK.get(self.severity, 0)


def _ddi(a, da, b, db, severity, description):
    return DrugInteraction(a, da, b, db, severity, description)


# Interactions among the RxNorm codes in normalize._MEDICATIONS.
_INTERACTIONS: list[DrugInteraction] = [
    _ddi("11289", "Warfarin", "1191", "Aspirin", "major",
         "Concurrent use increases the risk of serious bleeding."),
    _ddi("11289", "Warfarin", "5640", "Ibuprofen", "major",
         "NSAIDs increase bleeding risk and can potentiate anticoagulation."),
    _ddi("1191", "Aspirin", "5640", "Ibuprofen", "moderate",
         "Ibuprofen can blunt the antiplatelet effect of aspirin; additive GI risk."),
    _ddi("29046", "Lisinopril", "5640", "Ibuprofen", "moderate",
         "NSAIDs reduce ACE-inhibitor efficacy and may impair renal function."),
    _ddi("29046", "Lisinopril", "4603", "Furosemide", "moderate",
         "Risk of first-dose hypotension and reduced renal function."),
    _ddi("4603", "Furosemide", "5640", "Ibuprofen", "moderate",
         "NSAIDs reduce diuretic effect and increase nephrotoxicity risk."),
    _ddi("5487", "Hydrochlorothiazide", "5640", "Ibuprofen", "moderate",
         "NSAIDs reduce the antihypertensive and diuretic effect of thiazides."),
    _ddi("83367", "Atorvastatin", "17767", "Amlodipine", "moderate",
         "Amlodipine raises atorvastatin exposure; higher myopathy risk at high doses."),
    _ddi("274783", "Insulin glargine", "6918", "Metoprolol", "moderate",
         "Beta-blockers can mask the adrenergic warning signs of hypoglycemia."),
    _ddi("6809", "Metformin", "4603", "Furosemide", "minor",
         "Furosemide may increase metformin plasma levels; monitor renal function."),
]

# side_effect records keyed by RxNorm (SIDER-shaped).
_SIDE_EFFECTS: dict[str, list[str]] = {
    "6809": ["Diarrhea", "Nausea", "Lactic acidosis (rare)"],
    "11289": ["Bleeding", "Bruising"],
    "83367": ["Myalgia", "Elevated liver enzymes"],
    "29046": ["Dry cough", "Hyperkalemia"],
    "5640": ["GI upset", "Renal impairment"],
    "4603": ["Hypokalemia", "Dehydration"],
    "17767": ["Peripheral edema", "Flushing"],
    "6918": ["Bradycardia", "Fatigue"],
    "1191": ["GI bleeding", "Tinnitus"],
    "274783": ["Hypoglycemia", "Injection-site reaction"],
    "5487": ["Hypokalemia", "Photosensitivity"],
    "25480": ["Somnolence", "Dizziness"],
}

# Index by unordered code pair for O(1) lookup.
_BY_PAIR: dict[frozenset[str], DrugInteraction] = {i.pair_key(): i for i in _INTERACTIONS}


def interaction_for(rxnorm_a: str, rxnorm_b: str) -> DrugInteraction | None:
    """Return the known interaction between two RxNorm codes, if any."""
    return _BY_PAIR.get(frozenset({rxnorm_a, rxnorm_b}))


def all_interactions() -> list[DrugInteraction]:
    return list(_INTERACTIONS)


def side_effects_for(rxnorm: str) -> list[str]:
    return list(_SIDE_EFFECTS.get(rxnorm, []))
