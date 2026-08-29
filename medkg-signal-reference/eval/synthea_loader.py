#!/usr/bin/env python3
"""
Synthea Synthetic Cohort Loader for MedKG-Signal
==================================================

Parses a Synthea CSV export (from `synthea_generator.sh`) into a patient x
feature matrix suitable for the MedKG-Signal 5-model benchmark. Provides
a THIRD external validation cohort alongside PhysioNet Challenge 2012
and eICU-CRD Demo - this one is Apache-2.0 synthetic, so it can be
regenerated with a different seed for further robustness checks.

Prediction task: prospective 3-year all-cause mortality from a landmark
date (2023-01-01). Features are computed from observations, conditions,
and medications recorded strictly BEFORE the landmark. Labels are set to
1 if the patient's DEATHDATE lies between the landmark and the study
horizon (default 2026-08-29), 0 if the patient was alive at the landmark
and is either still alive at horizon or died after horizon.

Expected files under `data/synthea/output/csv/`:
  patients.csv        (Id, BIRTHDATE, DEATHDATE, GENDER, RACE, ...)
  conditions.csv      (START, PATIENT, CODE=SNOMED-CT, DESCRIPTION)
  observations.csv    (DATE, PATIENT, CATEGORY, CODE=LOINC, VALUE, TYPE)
  medications.csv     (START, PATIENT, CODE=RxNorm, DESCRIPTION)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Canonical vital-sign LOINC codes (Synthea populates these consistently)
# ---------------------------------------------------------------------------
VITAL_LOINC = {
    "8302-2": "body_height_cm",
    "29463-7": "body_weight_kg",
    "8867-4": "heart_rate_bpm",
    "9279-1": "respiratory_rate",
    "8310-5": "body_temperature_c",
    "8480-6": "sbp_mmhg",
    "8462-4": "dbp_mmhg",
    "2708-6": "spo2_pct",
    "72514-3": "pain_severity",
    "39156-5": "bmi_kgm2",
}

# 10 vitals x 6 summary stats = 60 signal features
SUMMARY_STATS = ("count", "min", "max", "mean", "std", "last")

# Landmark and horizon dates for prospective survival prediction.
# 2010-01-01 landmark gives ~9.5% 16-year all-cause mortality (comparable
# base-rate to eICU-CRD Demo at 8.5% and PhysioNet 2012 at 14%) while
# leaving 15+ years of Synthea history available for feature computation.
LANDMARK = pd.Timestamp("2010-01-01", tz="UTC")
HORIZON = pd.Timestamp("2026-08-29", tz="UTC")

# Top-K codes to include as text features
COND_TOP_K = 200
MED_TOP_K = 200


@dataclass
class SyntheaBundle:
    patient_ids: np.ndarray                  # (N,) UUID strings
    static: np.ndarray                       # (N, 4) age_at_landmark, gender, race_id, ethnicity_id
    signal_summary: np.ndarray               # (N, 60) vital summaries
    observed_mask: np.ndarray                # (N, len(VITAL_LOINC))
    observation_counts: np.ndarray           # (N, len(VITAL_LOINC))
    condition_bag: np.ndarray                # (N, COND_TOP_K)
    medication_bag: np.ndarray               # (N, MED_TOP_K)
    y_mortality: np.ndarray                  # (N,) 1 = died between landmark and horizon
    signal_columns: List[str]
    condition_codes: List[str]
    medication_codes: List[str]


def _summary_stats(values: pd.Series) -> np.ndarray:
    if values.empty:
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=np.float32)
    if arr.size == 0:
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    return np.array(
        [
            float(arr.size),
            float(arr.min()),
            float(arr.max()),
            float(arr.mean()),
            float(arr.std() if arr.size > 1 else 0.0),
            float(arr[-1]),
        ],
        dtype=np.float32,
    )


def load_synthea(csv_root: Path, verbose: bool = True) -> SyntheaBundle:
    csv_root = Path(csv_root)
    if verbose:
        print(f"Loading Synthea CSV export from: {csv_root}")

    patients = pd.read_csv(csv_root / "patients.csv", parse_dates=["BIRTHDATE", "DEATHDATE"])
    patients["BIRTHDATE"] = pd.to_datetime(patients["BIRTHDATE"], utc=True, errors="coerce")
    patients["DEATHDATE"] = pd.to_datetime(patients["DEATHDATE"], utc=True, errors="coerce")

    # Cohort filter: patients ALIVE at landmark
    alive_at_landmark = patients["DEATHDATE"].isna() | (patients["DEATHDATE"] > LANDMARK)
    born_before_landmark = patients["BIRTHDATE"] < LANDMARK
    cohort = patients[alive_at_landmark & born_before_landmark].reset_index(drop=True)

    # Label: died between landmark and horizon
    dd = cohort["DEATHDATE"]
    y = ((dd.notna()) & (dd <= HORIZON)).astype(int).to_numpy()

    patient_ids = cohort["Id"].to_numpy()
    if verbose:
        print(
            f"  cohort at landmark {LANDMARK.date()}: N={len(patient_ids):,} | "
            f"3-yr mortality={y.mean() * 100:.2f}% ({int(y.sum())} deaths by "
            f"horizon {HORIZON.date()})"
        )

    # Static features
    age_days = (LANDMARK - cohort["BIRTHDATE"]).dt.days.fillna(0).to_numpy(dtype=np.float32)
    age_years = age_days / 365.25
    gender_flag = (cohort["GENDER"].astype(str).str.upper() == "M").astype(np.float32).to_numpy()
    race_id = cohort["RACE"].astype("category").cat.codes.astype(np.float32).to_numpy()
    ethnicity_id = cohort["ETHNICITY"].astype("category").cat.codes.astype(np.float32).to_numpy()
    static = np.stack([age_years, gender_flag, race_id, ethnicity_id], axis=1).astype(np.float32)

    id_to_row = {pid: i for i, pid in enumerate(patient_ids)}

    # ------------------------------------------------------------------
    # Observations (vitals only, before landmark)
    # ------------------------------------------------------------------
    if verbose:
        print("  parsing observations.csv (vital signs before landmark)...")
    obs_iter = pd.read_csv(
        csv_root / "observations.csv",
        usecols=["DATE", "PATIENT", "CODE", "VALUE"],
        chunksize=200_000,
    )
    vital_frames: List[pd.DataFrame] = []
    for chunk in obs_iter:
        chunk = chunk[chunk["CODE"].astype(str).isin(VITAL_LOINC.keys())]
        if chunk.empty:
            continue
        chunk["DATE"] = pd.to_datetime(chunk["DATE"], utc=True, errors="coerce")
        chunk = chunk[chunk["DATE"] < LANDMARK]
        chunk = chunk[chunk["PATIENT"].isin(id_to_row)]
        if not chunk.empty:
            vital_frames.append(chunk)
    vitals = (
        pd.concat(vital_frames, ignore_index=True)
        if vital_frames
        else pd.DataFrame(columns=["DATE", "PATIENT", "CODE", "VALUE"])
    )

    n = len(patient_ids)
    codes = list(VITAL_LOINC.keys())
    signal_columns: List[str] = []
    for c in codes:
        signal_columns.extend([f"{VITAL_LOINC[c]}_{s}" for s in SUMMARY_STATS])
    signal_summary = np.zeros((n, len(codes) * len(SUMMARY_STATS)), dtype=np.float32)
    observed_mask = np.zeros((n, len(codes)), dtype=np.float32)
    obs_counts = np.zeros((n, len(codes)), dtype=np.float32)

    if not vitals.empty:
        vitals = vitals.sort_values(["PATIENT", "CODE", "DATE"])
        for (pid, code), grp in vitals.groupby(["PATIENT", "CODE"], sort=False):
            row = id_to_row.get(pid)
            if row is None:
                continue
            j = codes.index(code)
            slot = j * len(SUMMARY_STATS)
            signal_summary[row, slot : slot + len(SUMMARY_STATS)] = _summary_stats(grp["VALUE"])
            observed_mask[row, j] = 1.0
            obs_counts[row, j] = float(len(grp))

    # ------------------------------------------------------------------
    # Conditions before landmark - bag-of-SNOMED
    # ------------------------------------------------------------------
    if verbose:
        print("  parsing conditions.csv ...")
    cond = pd.read_csv(csv_root / "conditions.csv", usecols=["START", "PATIENT", "CODE"])
    cond["START"] = pd.to_datetime(cond["START"], utc=True, errors="coerce")
    cond = cond[(cond["START"] < LANDMARK) & (cond["PATIENT"].isin(id_to_row))]
    cond["CODE"] = cond["CODE"].astype(str)
    top_conditions = cond["CODE"].value_counts().head(COND_TOP_K).index.tolist()
    cond_code_to_col = {c: i for i, c in enumerate(top_conditions)}
    condition_bag = np.zeros((n, len(top_conditions)), dtype=np.float32)
    for pid, code in zip(cond["PATIENT"], cond["CODE"]):
        row = id_to_row.get(pid)
        col = cond_code_to_col.get(code)
        if row is not None and col is not None:
            condition_bag[row, col] = 1.0

    # ------------------------------------------------------------------
    # Medications before landmark - bag-of-RxNorm
    # ------------------------------------------------------------------
    if verbose:
        print("  parsing medications.csv ...")
    meds = pd.read_csv(csv_root / "medications.csv", usecols=["START", "PATIENT", "CODE"])
    meds["START"] = pd.to_datetime(meds["START"], utc=True, errors="coerce")
    meds = meds[(meds["START"] < LANDMARK) & (meds["PATIENT"].isin(id_to_row))]
    meds["CODE"] = meds["CODE"].astype(str)
    top_meds = meds["CODE"].value_counts().head(MED_TOP_K).index.tolist()
    med_code_to_col = {c: i for i, c in enumerate(top_meds)}
    medication_bag = np.zeros((n, len(top_meds)), dtype=np.float32)
    for pid, code in zip(meds["PATIENT"], meds["CODE"]):
        row = id_to_row.get(pid)
        col = med_code_to_col.get(code)
        if row is not None and col is not None:
            medication_bag[row, col] = 1.0

    return SyntheaBundle(
        patient_ids=patient_ids,
        static=static,
        signal_summary=signal_summary,
        observed_mask=observed_mask,
        observation_counts=obs_counts,
        condition_bag=condition_bag,
        medication_bag=medication_bag,
        y_mortality=y,
        signal_columns=signal_columns,
        condition_codes=top_conditions,
        medication_codes=top_meds,
    )


def stratified_split(
    y: np.ndarray,
    val_frac: float = 0.15,
    test_frac: float = 0.20,
    seed: int = 20260829,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    idx_pos = np.where(y == 1)[0]
    idx_neg = np.where(y == 0)[0]
    rng.shuffle(idx_pos)
    rng.shuffle(idx_neg)

    def _split(idx: np.ndarray):
        n = len(idx)
        n_test = int(round(n * test_frac))
        n_val = int(round(n * val_frac))
        return idx[n_test + n_val :], idx[n_test : n_test + n_val], idx[:n_test]

    tr_p, va_p, te_p = _split(idx_pos)
    tr_n, va_n, te_n = _split(idx_neg)
    tr = np.concatenate([tr_p, tr_n]); rng.shuffle(tr)
    va = np.concatenate([va_p, va_n]); rng.shuffle(va)
    te = np.concatenate([te_p, te_n]); rng.shuffle(te)
    return tr, va, te


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "data" / "synthea" / "output" / "csv"
    bundle = load_synthea(root)
    print(f"\nCohort N={len(bundle.patient_ids):,} | 3-yr mortality={bundle.y_mortality.mean() * 100:.2f}%")
    print(f"static           : {bundle.static.shape}")
    print(f"signal_summary   : {bundle.signal_summary.shape}")
    print(f"observed_mask    : {bundle.observed_mask.shape}")
    print(f"condition_bag    : {bundle.condition_bag.shape}")
    print(f"medication_bag   : {bundle.medication_bag.shape}")
