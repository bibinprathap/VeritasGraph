"""Re-identification risk metrics: k-anonymity over released cohorts.

Mirrors OpenMed ``risk/kanon.py``. Given quasi-identifiers per patient, compute
the k-anonymity of the release (the size of the smallest equivalence class) and
report which groups violate a target k.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class KAnonymityReport:
    k: int
    target_k: int
    satisfied: bool
    equivalence_classes: int
    violating_groups: list[dict]


def k_anonymity(
    records: list[dict],
    quasi_identifiers: list[str],
    target_k: int = 5,
) -> KAnonymityReport:
    """Compute k-anonymity for a list of released patient records."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        key = tuple(str(r.get(q, "")) for q in quasi_identifiers)
        groups[key].append(r)

    if not groups:
        return KAnonymityReport(0, target_k, False, 0, [])

    k = min(len(v) for v in groups.values())
    violating = [
        {
            "quasi_identifiers": dict(zip(quasi_identifiers, key)),
            "size": len(members),
        }
        for key, members in groups.items()
        if len(members) < target_k
    ]
    return KAnonymityReport(
        k=k,
        target_k=target_k,
        satisfied=k >= target_k,
        equivalence_classes=len(groups),
        violating_groups=violating,
    )
