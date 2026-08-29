#!/usr/bin/env python3
"""
eICU-CRD Demo Data Loader for MedKG-Signal
============================================

Parses the publicly-available eICU-CRD Demo (2,521 ICU stays, 208 US
hospitals) into a patient x feature matrix suitable for the MedKG-Signal
5-model benchmark. Provides an *independent* cross-cohort external
validation alongside PhysioNet Challenge 2012 (single-source MIMIC-II).

Expected data layout under `data/eicu_demo/`:
  patient.csv.gz                 patientunitstayid + demographics + outcome
  vitalPeriodic.csv.gz           5-minute automated vitals
  vitalAperiodic.csv.gz          nurse-recorded vitals
  lab.csv.gz                     lab results (labname, labresult)
  diagnosis.csv.gz               ICD-9/ICD-10 codes per stay
  apachePatientResult.csv.gz     APACHE IV mortality baseline (comparison)

Outputs a bundle with:
  static           : (N, 5)  age, gender_flag, admission_weight, unit_type,
                              apache_score
  signal_summary   : (N, 12*6=72) vital summary stats
  observed_mask    : (N, len(CANONICAL_LABS)) 0/1 whether lab was measured
  observation_counts: (N, len(CANONICAL_LABS)) log-scaled counts
  lab_summary      : (N, len(CANONICAL_LABS)*6) lab per-var summary stats
  diagnosis_bag    : (N, DIAG_TOP_K) binary indicator over top-k ICD codes
  y_mortality      : (N,) 0/1 hospitaldischargestatus == 'Expired'
  stay_ids         : (N,) patientunitstayid array
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Canonical variable groups
# ---------------------------------------------------------------------------
# 12 vitals grouped as (parameter, source_table). Aperiodic non-invasive
# BP is preferred over periodic invasive when only one is present per patient.
VITAL_VARS = [
    ("heartrate", "periodic"),
    ("temperature", "periodic"),
    ("respiration", "periodic"),
    ("sao2", "periodic"),
    ("systemicmean", "periodic"),          # invasive MAP
    ("systemicsystolic", "periodic"),
    ("systemicdiastolic", "periodic"),
    ("etco2", "periodic"),
    ("noninvasivemean", "aperiodic"),      # non-invasive MAP
    ("noninvasivesystolic", "aperiodic"),
    ("noninvasivediastolic", "aperiodic"),
    ("cvp", "periodic"),
]

# 24 canonical labs (LOINC-inspired, matching PhysioNet 2012's lab list)
CANONICAL_LABS = [
    "sodium", "potassium", "creatinine", "BUN", "glucose", "chloride",
    "bicarbonate", "calcium", "magnesium", "phosphate",
    "WBC x 1000", "Hgb", "Hct", "platelets x 1000", "MCV",
    "pH", "paO2", "paCO2", "lactate",
    "ALT (SGPT)", "AST (SGOT)", "total bilirubin", "albumin", "troponin - I",
]

SUMMARY_STATS = ("count", "min", "max", "mean", "std", "last")

DIAG_TOP_K = 200  # top-K ICD codes to use as the diagnosis bag-of-codes


@dataclass
class EICUBundle:
    stay_ids: np.ndarray                 # (N,)
    static: np.ndarray                   # (N, 5)
    signal_summary: np.ndarray           # (N, 72)
    observed_mask: np.ndarray            # (N, len(CANONICAL_LABS))
    observation_counts: np.ndarray       # (N, len(CANONICAL_LABS))
    lab_summary: np.ndarray              # (N, len(CANONICAL_LABS) * 6)
    diagnosis_bag: np.ndarray            # (N, DIAG_TOP_K)
    y_mortality: np.ndarray              # (N,)
    apache_pred: np.ndarray              # (N,) APACHE IV predictedhospitalmortality (may be NaN)
    diag_columns: List[str]
    signal_columns: List[str]
    lab_columns: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _summary_stats(values: pd.Series) -> np.ndarray:
    if values.empty:
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    arr = values.dropna().to_numpy(dtype=np.float32)
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


def _summarise_wide(
    df: pd.DataFrame, group_col: str, value_cols: List[str], stay_ids: np.ndarray
) -> np.ndarray:
    """Return (N, len(value_cols) * 6) summary matrix aligned to stay_ids."""
    if df is None or df.empty:
        return np.zeros(
            (stay_ids.size, len(value_cols) * len(SUMMARY_STATS)), dtype=np.float32
        )
    grouped = df.groupby(group_col, sort=False)
    out = np.zeros(
        (stay_ids.size, len(value_cols) * len(SUMMARY_STATS)), dtype=np.float32
    )
    stay_to_row = {int(s): i for i, s in enumerate(stay_ids)}
    for stay, g in grouped:
        row = stay_to_row.get(int(stay))
        if row is None:
            continue
        for j, col in enumerate(value_cols):
            slot = j * len(SUMMARY_STATS)
            out[row, slot : slot + len(SUMMARY_STATS)] = _summary_stats(g[col])
    return out


# ---------------------------------------------------------------------------
# Cohort loader
# ---------------------------------------------------------------------------
def load_eicu_demo(root: Path, verbose: bool = True) -> EICUBundle:
    root = Path(root)

    if verbose:
        print(f"Loading eICU-CRD Demo from: {root}")

    # 1. patient.csv - defines the cohort
    patient = pd.read_csv(root / "patient.csv.gz")
    # Keep only stays with a decisive discharge outcome
    valid = patient["hospitaldischargestatus"].isin(["Alive", "Expired"])
    patient = patient[valid].reset_index(drop=True)
    y = (patient["hospitaldischargestatus"] == "Expired").astype(int).to_numpy()
    stay_ids = patient["patientunitstayid"].astype(int).to_numpy()

    # Static features (age is a string like "> 89" for some patients)
    age = pd.to_numeric(patient["age"], errors="coerce").fillna(89.0).to_numpy(dtype=np.float32)
    gender = (patient["gender"].astype(str).str.strip() == "Male").astype(np.float32).to_numpy()
    weight = pd.to_numeric(patient["admissionweight"], errors="coerce").fillna(80.0).to_numpy(dtype=np.float32)
    unit_type = patient["unittype"].astype("category").cat.codes.astype(np.float32).to_numpy()

    if verbose:
        print(
            f"  cohort: N={len(stay_ids):,} | mortality={y.mean() * 100:.2f}% "
            f"({int(y.sum())} deaths)"
        )

    # 2. APACHE IV baseline (may be missing for some stays)
    apache_pred = np.full(len(stay_ids), np.nan, dtype=np.float32)
    apache_score = np.zeros(len(stay_ids), dtype=np.float32)
    try:
        apache = pd.read_csv(root / "apachePatientResult.csv.gz")
        # apacheversion == 'IV' is the modern one; keep highest apacheversion per stay
        apache = apache.sort_values(["patientunitstayid", "apacheversion"]).drop_duplicates(
            "patientunitstayid", keep="last"
        )
        # predictedhospitalmortality is in [0, 1] or -1 when missing
        pred = apache.set_index("patientunitstayid")["predictedhospitalmortality"]
        score = apache.set_index("patientunitstayid")["apachescore"]
        for i, s in enumerate(stay_ids):
            v = pred.get(int(s), np.nan)
            if pd.notna(v) and v >= 0:
                apache_pred[i] = float(v)
            v2 = score.get(int(s), np.nan)
            if pd.notna(v2) and v2 >= 0:
                apache_score[i] = float(v2)
    except FileNotFoundError:
        pass

    static = np.stack([age, gender, weight, unit_type, apache_score], axis=1).astype(
        np.float32
    )

    # 3. Vitals - periodic + aperiodic
    if verbose:
        print("  parsing vitalPeriodic.csv.gz ...")
    vp = pd.read_csv(
        root / "vitalPeriodic.csv.gz",
        usecols=["patientunitstayid"]
        + [v for v, src in VITAL_VARS if src == "periodic"],
    )
    if verbose:
        print("  parsing vitalAperiodic.csv.gz ...")
    va = pd.read_csv(
        root / "vitalAperiodic.csv.gz",
        usecols=["patientunitstayid"]
        + [v for v, src in VITAL_VARS if src == "aperiodic"],
    )

    signal_columns: List[str] = []
    signal_blocks: List[np.ndarray] = []
    for var, src in VITAL_VARS:
        df = vp if src == "periodic" else va
        block = _summarise_wide(df, "patientunitstayid", [var], stay_ids)
        signal_blocks.append(block)
        signal_columns.extend([f"{var}_{s}" for s in SUMMARY_STATS])
    signal_summary = np.concatenate(signal_blocks, axis=1).astype(np.float32)

    # 4. Labs
    if verbose:
        print("  parsing lab.csv.gz ...")
    lab = pd.read_csv(
        root / "lab.csv.gz",
        usecols=["patientunitstayid", "labname", "labresult"],
    )
    lab = lab[lab["labname"].isin(CANONICAL_LABS)]
    # Pivot: build one column per lab, then group
    observed_mask = np.zeros((len(stay_ids), len(CANONICAL_LABS)), dtype=np.float32)
    obs_counts = np.zeros((len(stay_ids), len(CANONICAL_LABS)), dtype=np.float32)
    lab_summary = np.zeros(
        (len(stay_ids), len(CANONICAL_LABS) * len(SUMMARY_STATS)), dtype=np.float32
    )
    lab_columns: List[str] = []
    for j, name in enumerate(CANONICAL_LABS):
        lab_columns.extend([f"{name}_{s}" for s in SUMMARY_STATS])
        sub = lab[lab["labname"] == name]
        if sub.empty:
            continue
        counts = sub.groupby("patientunitstayid").size()
        stay_to_row = {int(s): i for i, s in enumerate(stay_ids)}
        for stay, c in counts.items():
            row = stay_to_row.get(int(stay))
            if row is not None:
                observed_mask[row, j] = 1.0
                obs_counts[row, j] = float(c)
        block = _summarise_wide(sub, "patientunitstayid", ["labresult"], stay_ids)
        lab_summary[
            :, j * len(SUMMARY_STATS) : (j + 1) * len(SUMMARY_STATS)
        ] = block

    # 5. Diagnoses - bag-of-ICD (top-K on train pool = full cohort here; we
    # keep the ranking to be applied by the benchmark using its train mask)
    if verbose:
        print("  parsing diagnosis.csv.gz ...")
    diag = pd.read_csv(
        root / "diagnosis.csv.gz",
        usecols=["patientunitstayid", "icd9code"],
    )
    diag = diag.dropna(subset=["icd9code"])
    # Some rows carry multiple codes separated by comma: keep only the first
    diag["icd9code"] = diag["icd9code"].astype(str).str.split(",").str[0].str.strip()
    # Frequency ranking
    freq = diag["icd9code"].value_counts()
    top_codes = freq.head(DIAG_TOP_K).index.tolist()
    diag_columns = list(top_codes)
    code_to_col = {c: i for i, c in enumerate(top_codes)}

    diagnosis_bag = np.zeros((len(stay_ids), len(top_codes)), dtype=np.float32)
    stay_to_row = {int(s): i for i, s in enumerate(stay_ids)}
    for stay, code in zip(diag["patientunitstayid"], diag["icd9code"]):
        row = stay_to_row.get(int(stay))
        col = code_to_col.get(code)
        if row is not None and col is not None:
            diagnosis_bag[row, col] = 1.0

    return EICUBundle(
        stay_ids=stay_ids,
        static=static,
        signal_summary=signal_summary,
        observed_mask=observed_mask,
        observation_counts=obs_counts,
        lab_summary=lab_summary,
        diagnosis_bag=diagnosis_bag,
        y_mortality=y,
        apache_pred=apache_pred,
        diag_columns=diag_columns,
        signal_columns=signal_columns,
        lab_columns=lab_columns,
    )


# ---------------------------------------------------------------------------
# Deterministic stratified split
# ---------------------------------------------------------------------------
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
    root = Path(__file__).resolve().parents[1] / "data" / "eicu_demo"
    bundle = load_eicu_demo(root)
    print(
        f"\nCohort: N={len(bundle.stay_ids):,} | "
        f"mortality={bundle.y_mortality.mean() * 100:.2f}% "
        f"({int(bundle.y_mortality.sum())} deaths)"
    )
    print(f"static           : {bundle.static.shape}")
    print(f"signal_summary   : {bundle.signal_summary.shape}")
    print(f"observed_mask    : {bundle.observed_mask.shape}")
    print(f"lab_summary      : {bundle.lab_summary.shape}")
    print(f"diagnosis_bag    : {bundle.diagnosis_bag.shape}")
    apache_valid = np.isfinite(bundle.apache_pred).sum()
    print(f"APACHE IV baseline available for {apache_valid}/{len(bundle.stay_ids)} stays")
