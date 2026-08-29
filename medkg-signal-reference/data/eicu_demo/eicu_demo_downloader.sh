#!/usr/bin/env bash
# =============================================================================
# eICU-CRD Demo Dataset - Downloader Scaffold
# =============================================================================
# Downloads the eICU Collaborative Research Database Demo (100-patient sample).
# The demo is publicly available (no credentialing / no DUA) and mirrors the
# schema of the full 200k-patient eICU-CRD used in the medical-AI literature.
#
# Source: https://physionet.org/content/eicu-crd-demo/2.0.1/
# License: ODC-BY 1.0
#
# Usage:
#   ./eicu_demo_downloader.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="https://physionet.org/files/eicu-crd-demo/2.0.1"

# Core tables used by the 5-model benchmark
TABLES=(
    "patient.csv.gz"
    "apachePatientResult.csv.gz"
    "vitalPeriodic.csv.gz"
    "vitalAperiodic.csv.gz"
    "lab.csv.gz"
    "diagnosis.csv.gz"
    "treatment.csv.gz"
    "medication.csv.gz"
)

echo "Downloading eICU-CRD Demo (100 patients, ~50MB compressed)..."
for tbl in "${TABLES[@]}"; do
    if [[ ! -f "$SCRIPT_DIR/$tbl" ]]; then
        echo "  $tbl"
        curl -sSf -o "$SCRIPT_DIR/$tbl" "$BASE_URL/$tbl"
    else
        echo "  $tbl (already present)"
    fi
done

echo ""
echo "Files in $SCRIPT_DIR:"
ls -lh "$SCRIPT_DIR"/*.csv.gz 2>/dev/null
