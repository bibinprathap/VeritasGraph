#!/usr/bin/env python3
"""
PhysioNet Challenge 2012 Data Loader for MedKG-Signal
======================================================

Parses PhysioNet Challenge 2012 per-patient time-series records into a
patient x feature matrix suitable for the MedKG-Signal 5-model benchmark.

Data layout expected under `data/physionet2012/`:
  set-a/<RecordID>.txt          # 4,000 ICU stays
  set-b/<RecordID>.txt          # 4,000 ICU stays
  Outcomes-a.txt                # mortality labels for set-a
  Outcomes-b.txt                # mortality labels for set-b

Each patient .txt file has the format:
  Time,Parameter,Value
  00:00,RecordID,132539
  00:00,Age,54
  00:07,HR,73
  ...

We compute per-patient summary statistics (min/max/mean/std/last/count) over
the first 48 hours of ICU stay for the 37 canonical time-series variables
defined by the challenge, plus the 5 static descriptors (Age, Gender,
Height, Weight, ICUType). Missing values are encoded as -1 in the source
and are dropped before aggregation.

Output tensors:
  X_signal      : (N, ~30)   raw vital summary stats (HR, SpO2, GCS, MAP, ...)
  X_text        : (N, ~200)  bag-of-observed-variables + observation counts
                              (approximates a bag-of-clinical-codes baseline)
  X_all_summary : (N, ~250)  full per-variable summary matrix (used by
                              KG feature builder to compute co-occurrence)
  y_mortality   : (N,)       in-hospital death (0 = survived, 1 = died)
  record_ids    : (N,)       PhysioNet Challenge 2012 record IDs
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Canonical variable groups (PhysioNet Challenge 2012 spec)
# ---------------------------------------------------------------------------
# Static descriptors captured at t=00:00
STATIC_VARS = ["Age", "Gender", "Height", "Weight", "ICUType"]

# Vital signs (dense, high-frequency) - the "signal" modality
VITAL_VARS = [
    "HR",         # heart rate
    "Temp",       # core temperature
    "RespRate",   # respiratory rate
    "SysABP",     # invasive systolic blood pressure
    "DiasABP",    # invasive diastolic
    "MAP",        # invasive mean arterial pressure
    "NISysABP",   # non-invasive systolic
    "NIDiasABP",  # non-invasive diastolic
    "NIMAP",      # non-invasive mean
    "SaO2",       # arterial oxygen saturation
    "GCS",        # Glasgow coma scale
    "MechVent",   # binary indicator of mechanical ventilation
]

# Labs and derived measurements - the "text" (clinical-code) modality
LAB_VARS = [
    "ALP", "ALT", "AST", "Albumin", "BUN", "Bilirubin", "Cholesterol",
    "Creatinine", "FiO2", "Glucose", "HCO3", "HCT", "K", "Lactate", "Mg",
    "Na", "PaCO2", "PaO2", "Platelets", "TroponinI", "TroponinT",
    "Urine", "WBC", "pH",
]

ALL_TS_VARS = VITAL_VARS + LAB_VARS  # 12 + 24 = 36 canonical time series

# Summary statistics computed per (patient, variable)
SUMMARY_STATS = ("count", "min", "max", "mean", "std", "last")


@dataclass
class PhysioNet2012Bundle:
    """All arrays live on the same patient index (row order)."""

    record_ids: np.ndarray            # (N,)
    static: np.ndarray                # (N, 5)
    signal_summary: np.ndarray        # (N, len(VITAL_VARS) * len(SUMMARY_STATS))
    lab_summary: np.ndarray           # (N, len(LAB_VARS) * len(SUMMARY_STATS))
    observed_mask: np.ndarray         # (N, len(ALL_TS_VARS)) 0/1 whether variable was ever measured
    observation_counts: np.ndarray    # (N, len(ALL_TS_VARS)) raw counts per variable
    y_mortality: np.ndarray           # (N,) 0/1 in-hospital death
    signal_columns: List[str]         # column names for signal_summary
    lab_columns: List[str]            # column names for lab_summary
    observed_columns: List[str]       # column names for observed_mask / counts


# ---------------------------------------------------------------------------
# Per-patient parser
# ---------------------------------------------------------------------------
def _parse_patient_file(path: Path) -> Tuple[Dict[str, float], Dict[str, List[float]]]:
    """Return (static_dict, time_series_dict) for one patient file."""
    static: Dict[str, float] = {v: np.nan for v in STATIC_VARS}
    ts: Dict[str, List[float]] = {v: [] for v in ALL_TS_VARS}

    # Read raw lines; skip header. Robust to malformed lines.
    with open(path, "r") as f:
        f.readline()  # header "Time,Parameter,Value"
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) != 3:
                continue
            _time, param, value_str = parts
            try:
                value = float(value_str)
            except ValueError:
                continue
            # PhysioNet encodes missing as -1 for Height/Weight/etc.
            if param in STATIC_VARS:
                if value != -1:
                    static[param] = value
            elif param in ts:
                if value != -1 or param == "MechVent":
                    ts[param].append(value)
    return static, ts


def _summarise_ts(values: List[float]) -> np.ndarray:
    """Return per-variable summary vector [count, min, max, mean, std, last]."""
    if not values:
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    arr = np.asarray(values, dtype=np.float32)
    return np.array(
        [
            float(arr.size),
            float(arr.min()),
            float(arr.max()),
            float(arr.mean()),
            float(arr.std()),
            float(arr[-1]),
        ],
        dtype=np.float32,
    )


# ---------------------------------------------------------------------------
# Cohort loader
# ---------------------------------------------------------------------------
def _load_outcomes(outcomes_path: Path) -> pd.DataFrame:
    df = pd.read_csv(outcomes_path)
    if "In-hospital_death" not in df.columns:
        raise ValueError(f"Outcomes file missing In-hospital_death: {outcomes_path}")
    df["RecordID"] = df["RecordID"].astype(int)
    return df.set_index("RecordID")


def load_physionet2012(
    root: Path,
    sets: Tuple[str, ...] = ("set-a", "set-b"),
    verbose: bool = True,
) -> PhysioNet2012Bundle:
    root = Path(root)
    outcomes_files = {
        "set-a": root / "Outcomes-a.txt",
        "set-b": root / "Outcomes-b.txt",
    }
    signal_columns = [f"{v}_{s}" for v in VITAL_VARS for s in SUMMARY_STATS]
    lab_columns = [f"{v}_{s}" for v in LAB_VARS for s in SUMMARY_STATS]
    observed_columns = list(ALL_TS_VARS)

    record_ids: List[int] = []
    static_rows: List[np.ndarray] = []
    signal_rows: List[np.ndarray] = []
    lab_rows: List[np.ndarray] = []
    observed_rows: List[np.ndarray] = []
    count_rows: List[np.ndarray] = []
    y_rows: List[int] = []

    total_files = 0
    missing_outcomes = 0

    for set_name in sets:
        set_dir = root / set_name
        if not set_dir.exists():
            if verbose:
                print(f"  [skip] {set_dir} not found")
            continue
        outcomes = _load_outcomes(outcomes_files[set_name])
        files = sorted(set_dir.glob("*.txt"))
        if verbose:
            print(f"  {set_name}: {len(files)} patient files")
        for path in files:
            total_files += 1
            try:
                rec_id = int(path.stem)
            except ValueError:
                continue
            if rec_id not in outcomes.index:
                missing_outcomes += 1
                continue
            static, ts = _parse_patient_file(path)
            static_vec = np.array(
                [static[v] if not np.isnan(static[v]) else 0.0 for v in STATIC_VARS],
                dtype=np.float32,
            )
            # Signal summaries (vitals)
            signal_vec = np.concatenate(
                [_summarise_ts(ts[v]) for v in VITAL_VARS]
            )
            # Lab summaries
            lab_vec = np.concatenate([_summarise_ts(ts[v]) for v in LAB_VARS])
            # Observed / counts
            observed = np.array(
                [1.0 if ts[v] else 0.0 for v in ALL_TS_VARS], dtype=np.float32
            )
            counts = np.array([len(ts[v]) for v in ALL_TS_VARS], dtype=np.float32)

            record_ids.append(rec_id)
            static_rows.append(static_vec)
            signal_rows.append(signal_vec)
            lab_rows.append(lab_vec)
            observed_rows.append(observed)
            count_rows.append(counts)
            y_rows.append(int(outcomes.loc[rec_id, "In-hospital_death"]))

    if verbose:
        print(
            f"  parsed {total_files} files, "
            f"{len(record_ids)} joined with outcomes "
            f"({missing_outcomes} missing outcomes)"
        )

    return PhysioNet2012Bundle(
        record_ids=np.asarray(record_ids, dtype=np.int64),
        static=np.stack(static_rows),
        signal_summary=np.stack(signal_rows),
        lab_summary=np.stack(lab_rows),
        observed_mask=np.stack(observed_rows),
        observation_counts=np.stack(count_rows),
        y_mortality=np.asarray(y_rows, dtype=np.int64),
        signal_columns=signal_columns,
        lab_columns=lab_columns,
        observed_columns=observed_columns,
    )


# ---------------------------------------------------------------------------
# Deterministic train / val / test split
# ---------------------------------------------------------------------------
def stratified_split(
    y: np.ndarray,
    val_frac: float = 0.15,
    test_frac: float = 0.20,
    seed: int = 20260829,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic stratified split by y."""
    rng = np.random.default_rng(seed)
    idx_pos = np.where(y == 1)[0]
    idx_neg = np.where(y == 0)[0]
    rng.shuffle(idx_pos)
    rng.shuffle(idx_neg)

    def _split(idx: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        n = len(idx)
        n_test = int(round(n * test_frac))
        n_val = int(round(n * val_frac))
        te = idx[:n_test]
        va = idx[n_test : n_test + n_val]
        tr = idx[n_test + n_val :]
        return tr, va, te

    tr_p, va_p, te_p = _split(idx_pos)
    tr_n, va_n, te_n = _split(idx_neg)

    tr = np.concatenate([tr_p, tr_n])
    va = np.concatenate([va_p, va_n])
    te = np.concatenate([te_p, te_n])
    rng.shuffle(tr)
    rng.shuffle(va)
    rng.shuffle(te)
    return tr, va, te


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "data" / "physionet2012"
    print(f"Loading PhysioNet Challenge 2012 from: {root}")
    bundle = load_physionet2012(root)
    print(
        f"\nCohort: N={len(bundle.record_ids):,} | "
        f"mortality rate={bundle.y_mortality.mean() * 100:.2f}% "
        f"({int(bundle.y_mortality.sum())} deaths)"
    )
    print(f"Static features       : {bundle.static.shape}")
    print(f"Signal summary features: {bundle.signal_summary.shape}")
    print(f"Lab summary features   : {bundle.lab_summary.shape}")
    print(f"Observed indicator     : {bundle.observed_mask.shape}")
