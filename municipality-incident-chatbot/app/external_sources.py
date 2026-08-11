"""External corroboration connectors (Services & Data Layer).

Per the design (``02_why_this_architecture.md`` §4 and the dashed-line contract
in the context diagram), these sources *strengthen* a decision but are never a
hard dependency: if a source is offline, its signal is simply absent and fusion
caps the outcome at "needs review".

The connectors here are **simulated** — they model what a real CCTV/VMS API or
IoT hub would return, keyed off the incident's location. Replace a connector's
``fetch`` with a real API call and nothing else changes
(see ``03_how_to_modify.md`` §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Corroboration:
    """Evidence gathered from an external source near the incident."""

    cctv_confidence: Optional[float] = None      # CV confidence on a CCTV frame
    sensor_signal: Optional[float] = None        # normalised 0..1 telemetry
    details: List[str] = field(default_factory=list)

    def available(self) -> bool:
        return self.cctv_confidence is not None or self.sensor_signal is not None


# Zones that have municipal CCTV cameras and IoT sensors installed. Reports
# outside these zones simply get no corroboration (and are capped at review).
INSTRUMENTED_ZONES = {"downtown", "market", "central", "zone-1"}


class ExternalSources:
    """Aggregates CCTV + IoT-sensor corroboration for a location."""

    def __init__(self, cctv_online: bool = True, sensors_online: bool = True) -> None:
        self.cctv_online = cctv_online
        self.sensors_online = sensors_online

    def fetch(
        self, incident_code: str, location: Optional[Dict[str, Any]]
    ) -> Corroboration:
        corr = Corroboration()
        if location is None:
            return corr
        zone = str(location.get("zone", "")).lower()
        instrumented = zone in INSTRUMENTED_ZONES
        if not instrumented:
            return corr  # no cameras/sensors here -> corroboration unavailable

        # --- CCTV corroboration ------------------------------------------
        # Simulated: cameras cover known zones; a frame is analysed by the same
        # CV service in the real system.
        if self.cctv_online:
            corr.cctv_confidence = 0.87
            corr.details.append(f"CCTV frame near {zone} corroborates the report (0.87).")

        # --- IoT sensor corroboration ------------------------------------
        if self.sensors_online:
            if incident_code == "trash_overflow":
                corr.sensor_signal = 0.96
                corr.details.append("Bin fill-level sensor reads 96%.")
            elif incident_code == "overcrowding":
                corr.sensor_signal = 0.82
                corr.details.append("People-counter density above threshold (0.82).")
        return corr
