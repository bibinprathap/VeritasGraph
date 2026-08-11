#!/usr/bin/env python3
"""Interactive CLI demo for the Municipality Incident Reporting Chatbot.

Run from the repo root (VeritasGraph must be importable):

    python -m municipality_incident_chatbot.cli        # if installed as a pkg
    # or, from this folder:
    python cli.py

Attach a photo by typing:  <your message> | photo=/path/to/img.jpg
Set a location with:       <your message> | zone=downtown
Combine:                   trash overflowing here | photo=trash.jpg | zone=downtown
Type 'cases' to list registered cases, 'quit' to exit.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a loose script from within the folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import IncidentChatbot  # noqa: E402


def _parse(line: str):
    parts = [p.strip() for p in line.split("|")]
    text = parts[0]
    image_path = None
    location = {}
    for part in parts[1:]:
        if part.startswith("photo="):
            image_path = part[len("photo="):].strip()
        elif part.startswith("zone="):
            location["zone"] = part[len("zone="):].strip().lower()
        elif part.startswith("lat="):
            location["lat"] = float(part[len("lat="):])
        elif part.startswith("lon="):
            location["lon"] = float(part[len("lon="):])
    return text, image_path, (location or None)


def main() -> None:
    bot = IncidentChatbot()
    print("🏛️  Department of Municipality — Incident Reporting Chatbot")
    print("    (powered by VeritasGraph GraphRAG)\n")
    print("Describe your issue. Examples:")
    print("  trash overflowing near the market | photo=garbage_overflow.jpg | zone=downtown")
    print("  car abandoned for weeks | photo=car_wreck.jpg | zone=zone-1")
    print("Type 'cases' to list cases, 'quit' to exit.\n")

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"quit", "exit"}:
            break
        if line.lower() == "cases":
            for c in bot.cases.all():
                print(f"  {c['id']}  {c['incident_code']:<18} {c['status']:<14} "
                      f"score={c['validation_score']}")
            continue

        text, image_path, location = _parse(line)
        result = bot.handle_report(text, image_path=image_path, location=location)
        print(f"\nbot> {result.message}")
        if result.reasoning_path:
            print("     reasoning: " + " ; ".join(result.reasoning_path))
        print()


if __name__ == "__main__":
    main()
