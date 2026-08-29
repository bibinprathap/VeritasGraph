#!/usr/bin/env bash
# =============================================================================
# Synthea Synthetic Patient Generator - Scaffold
# =============================================================================
# Generates a synthetic patient cohort with realistic longitudinal EHR
# structure (conditions, encounters, observations, medications). Used as a
# secondary validation cohort for the MedKG-Signal 5-model benchmark.
#
# License: Apache-2.0 (synthea itself)
# Output license: Public / research-friendly (no PHI, fully synthetic)
#
# Usage:
#   ./synthea_generator.sh [POPULATION] [SEED]
#
# Requires Java 11+.
# =============================================================================

set -euo pipefail

POPULATION="${1:-1000}"
SEED="${2:-20260829}"
STATE="Massachusetts"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR"
SYNTHEA_DIR="$SCRIPT_DIR/synthea-src"
JAR_URL="https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar"
JAR_PATH="$SCRIPT_DIR/synthea-with-dependencies.jar"

if ! command -v java >/dev/null 2>&1; then
    echo "ERROR: Java 11+ is required. Install with 'sudo apt install openjdk-17-jre-headless'." >&2
    exit 1
fi

if [[ ! -f "$JAR_PATH" ]]; then
    echo "Downloading Synthea jar (~40MB)..."
    curl -L -o "$JAR_PATH" "$JAR_URL"
fi

echo "Generating $POPULATION synthetic patients (seed=$SEED, state=$STATE)..."
java -jar "$JAR_PATH" \
    -p "$POPULATION" \
    -s "$SEED" \
    -cs "$SEED" \
    --exporter.csv.export=true \
    --exporter.fhir.export=false \
    --exporter.baseDirectory="$OUT_DIR/output" \
    "$STATE"

echo ""
echo "Generated files in: $OUT_DIR/output/csv/"
ls -lh "$OUT_DIR/output/csv/" 2>/dev/null | head -20
