# Synthea Synthetic Patient Cohort (Scaffold)

## Purpose

Generates a **secondary validation cohort** of synthetic patients with
realistic longitudinal EHR structure. Used to demonstrate that MedKG-Signal
generalises beyond the PhysioNet Challenge 2012 ICU cohort.

## Why Synthea

- **Apache-2.0 licensed** (no DUA, no PHI concerns)
- Produces **conditions, encounters, observations, medications, allergies**
  in a natural EHR schema that maps directly onto our KG entity types
- Configurable cohort size (1k, 10k, 100k)
- Widely used in the medical-informatics community

## Usage

```bash
# Requires Java 11+
sudo apt install openjdk-17-jre-headless

# Generate 1,000 patients (fast, ~5 min)
./synthea_generator.sh 1000

# Generate 10,000 patients (paper-grade cohort, ~40 min)
./synthea_generator.sh 10000
```

Output lands in `data/synthea/output/csv/` and includes:
- `patients.csv`     — demographics, mortality
- `encounters.csv`   — visit records
- `conditions.csv`   — SNOMED-coded diagnoses
- `observations.csv` — vitals + labs (LOINC-coded)
- `medications.csv`  — RxNorm-coded prescriptions
- `procedures.csv`   — CPT-coded procedures

## Integration with the 5-Model Benchmark

A companion loader (`eval/synthea_loader.py`) will:
1. Aggregate `observations.csv` per patient (vital & lab summaries) → **signal features**
2. Bag-of-conditions from `conditions.csv` → **text features**
3. Co-occurrence graph on condition-observation-medication triples → **graph features**
4. Derive mortality label from `patients.csv` (`DEATHDATE` non-null)
5. Run the same 5-model contract as `physionet2012_benchmark.py`.

## Status

Scaffold only. Enable when time permits — PhysioNet 2012 already provides
a real-outcome cohort large enough to strengthen the ICSPIS 2026 paper.
