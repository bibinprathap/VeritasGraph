# eICU-CRD Demo Dataset (Scaffold)

## Purpose

**Sanity-check cohort** — the 100-patient eICU Collaborative Research
Database Demo confirms that the MedKG-Signal pipeline generalises to a
different real ICU data source without any code change beyond the loader.

## Why the eICU-CRD Demo

- **Publicly available** (no credentialing, no DUA) — unlike the full
  200k-patient eICU-CRD which requires a PhysioNet credentialed account
- Mirrors the schema of the full dataset (same tables, same columns)
- ODC-BY 1.0 licensed
- Complements PhysioNet Challenge 2012 by using a **different ICU
  network** (208 US hospitals) and a **different collection era** (2014–2015)

## Usage

```bash
# Downloads ~50MB of gzipped CSVs
./eicu_demo_downloader.sh
```

Tables downloaded:
- `patient.csv.gz`        — demographics + `hospitaldischargestatus`
- `apachePatientResult.csv.gz` — APACHE IV mortality prediction (comparison baseline)
- `vitalPeriodic.csv.gz`   — 5-minute vital-sign time series
- `vitalAperiodic.csv.gz`  — nurse-recorded vitals
- `lab.csv.gz`             — lab results (LOINC-friendly)
- `diagnosis.csv.gz`       — ICD-9 / ICD-10 codes
- `treatment.csv.gz`
- `medication.csv.gz`

## Integration with the 5-Model Benchmark

A companion loader (`eval/eicu_loader.py`) will:
1. Aggregate `vitalPeriodic.csv.gz` and `vitalAperiodic.csv.gz` →
   **signal features** (mirroring the PhysioNet 2012 signal block)
2. Bag-of-diagnoses from `diagnosis.csv.gz` → **text features**
3. Co-occurrence graph on (diagnosis, lab, treatment) triples →
   **graph features**
4. Derive mortality from `patient.hospitaldischargestatus == 'Expired'`
5. Run the same 5-model contract as `physionet2012_benchmark.py`.

## Cohort Size

100 patients — too small for a headline result on its own, but useful as
a **cross-cohort transfer test**: train on PhysioNet 2012, evaluate on
eICU demo without retraining. Adds credibility to the ICSPIS 2026 paper's
generalisation claim.

## Status

Scaffold only. Enable after the primary PhysioNet 2012 result is baked
into the paper.
