"""Municipal knowledge-graph seed data.

Expressed as a generic node/edge JSON graph that VeritasGraph's
``import_graph`` understands (see ``studio_api.graphrag_engine``). Non-reserved
node keys (``aliases``, ``cv_labels``, ``min_confidence``, ``contact``,
``response_hours``, ``priority``) are preserved as node metadata.

To add a new incident category, add an ``incident_type`` node + a
``responsible_for`` edge + an ``has_sla`` edge (see ``03_how_to_modify.md`` §1).
"""

from __future__ import annotations

from typing import Any, Dict


def municipal_graph() -> Dict[str, Any]:
    """Return the seed knowledge graph for the Department of Municipality."""
    nodes = [
        # ---- Incident types -------------------------------------------------
        {
            "id": "trash_overflow",
            "name": "Trash Overflow",
            "type": "incident_type",
            "description": "Garbage or waste overflowing from bins or dumped in public areas.",
            "aliases": ["trash", "garbage", "waste", "rubbish", "litter",
                         "overflow", "dump", "dumping", "bin", "dustbin", "smell"],
            "cv_labels": ["garbage", "trash_bag", "overflowing_bin", "waste_pile"],
            "min_confidence": 0.55,
        },
        {
            "id": "abandoned_vehicle",
            "name": "Abandoned Vehicle",
            "type": "incident_type",
            "description": "A vehicle left unattended, wrecked, or dumped on public land.",
            "aliases": ["abandoned", "abandoned vehicle", "dumped car", "scrap car",
                         "wreck", "junk car", "unattended vehicle"],
            "cv_labels": ["car", "truck", "bus"],
            "min_confidence": 0.6,
        },
        {
            "id": "overcrowding",
            "name": "Overcrowding",
            "type": "incident_type",
            "description": "Dangerous overcrowding or unauthorised mass gathering in a public space.",
            "aliases": ["crowd", "overcrowd", "overcrowding", "gathering",
                         "too many people", "stampede", "mass gathering"],
            "cv_labels": ["person", "crowd"],
            "min_confidence": 0.5,
        },
        {
            "id": "illegal_parking",
            "name": "Illegal Parking",
            "type": "incident_type",
            "description": "A vehicle parked illegally, blocking access, or in a no-parking zone.",
            "aliases": ["illegal parking", "no parking", "blocking", "double park",
                         "double parking", "parked illegally", "wrong parking",
                         "blocked road", "obstruction"],
            "cv_labels": ["car", "truck", "motorcycle"],
            "min_confidence": 0.6,
        },
        # ---- Departments ----------------------------------------------------
        {
            "id": "dept_sanitation",
            "name": "Sanitation Department",
            "type": "department",
            "description": "Responsible for waste collection and public cleanliness.",
            "contact": "sanitation@municipality.gov",
        },
        {
            "id": "dept_transport",
            "name": "Transport Department",
            "type": "department",
            "description": "Responsible for vehicle removal and roadworthiness.",
            "contact": "transport@municipality.gov",
        },
        {
            "id": "dept_public_safety",
            "name": "Public Safety Department",
            "type": "department",
            "description": "Responsible for crowd control and public safety.",
            "contact": "safety@municipality.gov",
        },
        {
            "id": "dept_traffic",
            "name": "Traffic Police",
            "type": "department",
            "description": "Responsible for enforcing parking and traffic rules.",
            "contact": "traffic@municipality.gov",
        },
        # ---- SLAs -----------------------------------------------------------
        {
            "id": "sla_trash",
            "name": "Trash Overflow SLA",
            "type": "sla",
            "description": "Waste must be cleared within 24 hours.",
            "response_hours": 24,
            "priority": "high",
        },
        {
            "id": "sla_vehicle",
            "name": "Abandoned Vehicle SLA",
            "type": "sla",
            "description": "Vehicle must be assessed and towed within 72 hours.",
            "response_hours": 72,
            "priority": "medium",
        },
        {
            "id": "sla_crowd",
            "name": "Overcrowding SLA",
            "type": "sla",
            "description": "Crowd situations must be attended within 6 hours.",
            "response_hours": 6,
            "priority": "high",
        },
        {
            "id": "sla_parking",
            "name": "Illegal Parking SLA",
            "type": "sla",
            "description": "Illegal parking must be actioned within 12 hours.",
            "response_hours": 12,
            "priority": "medium",
        },
        # ---- Policies -------------------------------------------------------
        {
            "id": "policy_waste",
            "name": "Solid Waste Management Policy",
            "type": "policy",
            "description": "Public bins must not overflow; overflow is a sanitation violation.",
        },
        {
            "id": "policy_parking",
            "name": "Municipal Parking Bylaw",
            "type": "policy",
            "description": "Parking is prohibited in marked no-parking and emergency zones.",
        },
    ]

    edges = [
        # incident -> responsible department
        {"source": "trash_overflow", "target": "dept_sanitation", "description": "responsible_for"},
        {"source": "abandoned_vehicle", "target": "dept_transport", "description": "responsible_for"},
        {"source": "overcrowding", "target": "dept_public_safety", "description": "responsible_for"},
        {"source": "illegal_parking", "target": "dept_traffic", "description": "responsible_for"},
        # incident -> SLA
        {"source": "trash_overflow", "target": "sla_trash", "description": "has_sla"},
        {"source": "abandoned_vehicle", "target": "sla_vehicle", "description": "has_sla"},
        {"source": "overcrowding", "target": "sla_crowd", "description": "has_sla"},
        {"source": "illegal_parking", "target": "sla_parking", "description": "has_sla"},
        # incident -> governing policy
        {"source": "trash_overflow", "target": "policy_waste", "description": "governed_by"},
        {"source": "illegal_parking", "target": "policy_parking", "description": "governed_by"},
    ]

    return {"nodes": nodes, "edges": edges, "title": "Department of Municipality KG"}
