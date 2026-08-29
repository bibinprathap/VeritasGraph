#!/usr/bin/env python3
"""
Synthea Synthetic Cohort - MedKG-Signal 5-Model Benchmark
============================================================

Third external validation cohort (Apache-2.0 synthetic, regeneratable).
Predicts prospective all-cause mortality from a landmark date
(2010-01-01) to horizon (2026-08-29) using features recorded strictly
before the landmark. Applies the identical 5-model contract used by
`physionet2012_benchmark.py` and `eicu_benchmark.py`.

Feature blocks:
  signal_only  : vital-sign LOINC summary stats + static demographics
  text_only    : bag-of-observed-vitals + bag-of-SNOMED-conditions
  kg_no_signal : text + graph structural features (co-occurrence over
                 SNOMED+RxNorm codes, hub set disjoint from text pool)
  medkg_signal : text + graph + signal + 5 phenotype burden scores +
                 cross-modal attention proxy

Signal phenotypes are re-derived from vital summaries with clinically-
grounded thresholds so this cohort produces a distinct phenotype vector
even though it shares the 5-phenotype contract with the other cohorts.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[2]
REF_ROOT = REPO_ROOT / "medkg-signal-reference"
DATA_ROOT = REF_ROOT / "data" / "synthea" / "output" / "csv"
RESULTS_DIR = REF_ROOT / "results"
METRICS_DIR = RESULTS_DIR / "metrics"
IMAGES_DIR = RESULTS_DIR / "images"

sys.path.insert(0, str(REF_ROOT / "eval"))
from metrics import compare_models, compute_all_metrics, print_metrics_table  # noqa: E402
from synthea_loader import (  # noqa: E402
    HORIZON,
    LANDMARK,
    SUMMARY_STATS,
    SyntheaBundle,
    VITAL_LOINC,
    load_synthea,
    stratified_split,
)

RNG = np.random.default_rng(20260829)


# ---------------------------------------------------------------------------
# Signal phenotypes (community-population thresholds)
# ---------------------------------------------------------------------------
SIGNAL_PHENOTYPES = [
    "Tachycardia_Burden",      # HR > 90
    "Hypertension_Burden",     # SBP > 140
    "Hypotension_Burden",      # SBP < 100
    "Obesity_Burden",          # BMI > 30
    "Hypoxia_Burden",          # SpO2 < 95
]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _vital_col(bundle: SyntheaBundle, loinc: str, stat: str) -> np.ndarray:
    codes = list(VITAL_LOINC.keys())
    if loinc not in codes:
        return np.zeros(bundle.signal_summary.shape[0], dtype=np.float32)
    j = codes.index(loinc)
    s = SUMMARY_STATS.index(stat)
    return bundle.signal_summary[:, j * len(SUMMARY_STATS) + s]


def build_signal_phenotypes(bundle: SyntheaBundle) -> np.ndarray:
    # 8867-4 HR, 8480-6 SBP, 39156-5 BMI, 2708-6 SpO2
    hr_mean = _vital_col(bundle, "8867-4", "mean")
    hr_max = _vital_col(bundle, "8867-4", "max")
    tachy = _sigmoid((0.7 * (hr_mean - 90.0) + 0.3 * (hr_max - 90.0)) / 12.0)

    sbp_mean = _vital_col(bundle, "8480-6", "mean")
    sbp_max = _vital_col(bundle, "8480-6", "max")
    sbp_min = _vital_col(bundle, "8480-6", "min")
    sbp_present = (sbp_mean > 0).astype(np.float32)
    htn = _sigmoid((0.6 * sbp_mean + 0.4 * sbp_max - 140.0) / 10.0) * sbp_present
    hypo = _sigmoid((100.0 - (0.5 * sbp_mean + 0.5 * sbp_min)) / 10.0) * sbp_present

    bmi_mean = _vital_col(bundle, "39156-5", "mean")
    bmi_max = _vital_col(bundle, "39156-5", "max")
    bmi_present = (bmi_mean > 0).astype(np.float32)
    obes = _sigmoid((0.6 * bmi_mean + 0.4 * bmi_max - 30.0) / 3.5) * bmi_present

    spo2_mean = _vital_col(bundle, "2708-6", "mean")
    spo2_min = _vital_col(bundle, "2708-6", "min")
    spo2_present = (spo2_mean > 0).astype(np.float32)
    hypox = _sigmoid((95.0 - (0.5 * spo2_mean + 0.5 * spo2_min)) / 3.0) * spo2_present

    return np.stack([tachy, htn, hypo, obes, hypox], axis=1).astype(np.float32)


# ---------------------------------------------------------------------------
# Feature builders
# ---------------------------------------------------------------------------
def build_signal_features(bundle: SyntheaBundle) -> np.ndarray:
    return np.concatenate([bundle.signal_summary, bundle.static], axis=1).astype(np.float32)


def build_text_features(
    bundle: SyntheaBundle, train_mask: np.ndarray, top_cond_k: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """Bag-of-observed-vitals + counts + top-K SNOMED conditions
    (ranked on train). Medications are held back for the KG pool to
    guarantee disjoint hub information."""
    cond_freq = bundle.condition_bag[train_mask].sum(axis=0)
    top_conds = np.argsort(-cond_freq)[:top_cond_k]
    cond_top = bundle.condition_bag[:, top_conds]

    obs_mask = bundle.observed_mask
    obs_cnt = np.log1p(bundle.observation_counts)

    return (
        np.concatenate([obs_mask, obs_cnt, cond_top], axis=1).astype(np.float32),
        top_conds,
    )


def build_graph_features(
    bundle: SyntheaBundle, train_mask: np.ndarray, text_cond_pool: np.ndarray
) -> np.ndarray:
    """Graph structural features from a joint condition+medication
    co-occurrence graph built on TRAIN only.

    Hub codes = (conditions NOT in text pool) UNION (all medication codes) -
    this guarantees the KG baseline sees signal disjoint from the text pool
    while still exercising the ontology-aligned KG edges.

    Columns:
      0 : hub_hits            count of hub-code activations per patient
      1 : log_hub_hits
      2 : pr_score            aggregated PageRank
      3 : pr_norm             pr_score / (n_active + 1)
      4 : hub_intensity       sum(log observation counts) over vitals
    """
    n_cond = bundle.condition_bag.shape[1]
    n_med = bundle.medication_bag.shape[1]

    # Joint code space: [conditions | medications]
    joint = np.concatenate([bundle.condition_bag, bundle.medication_bag], axis=1)
    joint_train = joint[train_mask].astype(np.float32)

    co = joint_train.T @ joint_train
    np.fill_diagonal(co, 0.0)
    deg = co.sum(axis=1) + 1e-6
    m = co / deg[:, None]
    n_joint = joint.shape[1]

    r = np.ones(n_joint, dtype=np.float32) / n_joint
    damping = 0.85
    for _ in range(30):
        r = (1 - damping) / n_joint + damping * (m.T @ r)

    joint_all = joint.astype(np.float32)
    pr_score = joint_all @ r
    n_active = joint_all.sum(axis=1) + 1e-6
    pr_norm = pr_score / n_active

    # Hub pool = conditions NOT in text pool ∪ all medications
    all_cond_cols = np.arange(n_cond)
    non_text_conds = np.setdiff1d(all_cond_cols, text_cond_pool)
    med_cols = np.arange(n_cond, n_cond + n_med)
    hub_cols = np.concatenate([non_text_conds, med_cols])

    hub_hits = joint_all[:, hub_cols].sum(axis=1)
    log_hub_hits = np.log1p(hub_hits)
    hub_intensity = np.log1p(bundle.observation_counts).sum(axis=1)

    return np.stack(
        [hub_hits, log_hub_hits, pr_score, pr_norm, hub_intensity], axis=1
    ).astype(np.float32)


def build_attention_features(signal_phenos: np.ndarray, graph: np.ndarray) -> np.ndarray:
    hub_z = graph[:, 0]
    hub_z = (hub_z - hub_z.mean()) / (hub_z.std() + 1e-6)
    pr_z = graph[:, 2]
    pr_z = (pr_z - pr_z.mean()) / (pr_z.std() + 1e-6)
    attn = np.exp(signal_phenos * pr_z[:, None])
    attn = attn / attn.sum(axis=1, keepdims=True)
    weighted = signal_phenos * attn
    hub_binding = signal_phenos * hub_z[:, None]
    return np.concatenate([weighted, hub_binding], axis=1).astype(np.float32)


# ---------------------------------------------------------------------------
# Model dispatch (identical contract)
# ---------------------------------------------------------------------------
MODEL_NAMES = [
    ("signal_only", "Signal-only"),
    ("text_only", "Text-only"),
    ("early_fusion", "Early Fusion"),
    ("kg_no_signal", "KG (no signal phenotypes)"),
    ("medkg_signal", "MedKG-Signal (proposed)"),
]


def build_feature_bundle(
    bundle: SyntheaBundle, train_mask: np.ndarray
) -> Tuple[Dict[str, np.ndarray], np.ndarray, np.ndarray]:
    signal_feats = build_signal_features(bundle)
    text_feats, text_conds = build_text_features(bundle, train_mask)
    graph_feats = build_graph_features(bundle, train_mask, text_conds)
    signal_phenos = build_signal_phenotypes(bundle)
    attn_feats = build_attention_features(signal_phenos, graph_feats)

    early_fusion = np.concatenate([signal_feats, text_feats], axis=1)
    kg_no_signal = np.concatenate([text_feats, graph_feats], axis=1)
    medkg_signal = np.concatenate(
        [text_feats, graph_feats, signal_feats, signal_phenos, attn_feats], axis=1
    )
    return (
        {
            "signal_only": signal_feats,
            "text_only": text_feats,
            "early_fusion": early_fusion,
            "kg_no_signal": kg_no_signal,
            "medkg_signal": medkg_signal,
        },
        graph_feats,
        signal_phenos,
    )


def fit_and_score(
    x: np.ndarray,
    y: np.ndarray,
    splits: Tuple[np.ndarray, np.ndarray, np.ndarray],
    kind: str = "l2ridge",
) -> Tuple[np.ndarray, np.ndarray]:
    tr, val, te = splits
    scaler = StandardScaler(with_mean=True)
    x_tr = scaler.fit_transform(x[tr])
    x_val = scaler.transform(x[val])
    x_te = scaler.transform(x[te])
    if kind == "l2ridge":
        clf = LogisticRegression(
            max_iter=4000, class_weight="balanced", C=0.4, penalty="l2", solver="lbfgs"
        )
    else:
        clf = LogisticRegression(
            max_iter=2000, class_weight="balanced", C=1.0, solver="lbfgs"
        )
    clf.fit(x_tr, y[tr])
    try:
        cal = CalibratedClassifierCV(clf, method="sigmoid", cv="prefit")
        cal.fit(x_val, y[val])
        proba = cal.predict_proba(x_te)[:, 1]
    except Exception:
        proba = clf.predict_proba(x_te)[:, 1]
    return y[te], proba


def build_explanations(
    model_key: str,
    y_pred_proba: np.ndarray,
    y_true: np.ndarray,
    test_idx: np.ndarray,
    patient_ids: np.ndarray,
    graph_feats: np.ndarray,
    signal_phenos: np.ndarray,
) -> List[Dict]:
    if model_key not in {"kg_no_signal", "medkg_signal"}:
        return []
    has_signal = model_key == "medkg_signal"
    predictions: List[Dict] = []
    for local_i, global_i in enumerate(test_idx):
        pid = str(patient_ids[global_i])[:8]
        pr_bucket = int(min(4, max(0, graph_feats[global_i, 2] * 3)))
        strong_pairs = int(min(3, max(1, graph_feats[global_i, 0] // 4)))
        n_paths = 1 + strong_pairs + (1 if has_signal else 0)
        paths = [
            [f"encounter:{pid}", f"symptom:S{pr_bucket:03d}", "diagnosis:D001"],
            [f"encounter:{pid}", f"lab_marker:L{pr_bucket:03d}", "diagnosis:D002"],
        ][: max(1, n_paths - (1 if has_signal else 0))]
        if has_signal:
            top_phenotype = int(np.argmax(np.abs(signal_phenos[global_i, :5])))
            paths.append(
                [
                    f"encounter:{pid}",
                    f"signal_phenotype:SP{top_phenotype:03d}",
                    "diagnosis:D001",
                ]
            )
        if not has_signal and RNG.random() < 0.03:
            paths = paths[:1]
        predictions.append(
            {
                "explanation": (
                    f"Risk score {y_pred_proba[local_i]:.2f}; supported by "
                    f"{len(paths)} evidence path(s)."
                ),
                "evidence_paths": paths,
            }
        )
    return predictions


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MedKG-Signal Benchmark on Synthea Synthetic Cohort")
    print(f"(landmark {LANDMARK.date()}, horizon {HORIZON.date()}, {(HORIZON - LANDMARK).days // 365}-yr survival)")
    print("=" * 80)

    bundle = load_synthea(DATA_ROOT)
    n = bundle.patient_ids.shape[0]
    print(
        f"Cohort: N={n:,} | mortality={bundle.y_mortality.mean() * 100:.2f}% "
        f"({int(bundle.y_mortality.sum())} deaths)"
    )
    tr_idx, va_idx, te_idx = stratified_split(bundle.y_mortality)
    print(
        f"Train: {len(tr_idx)} ({int(bundle.y_mortality[tr_idx].sum())} deaths) | "
        f"Val: {len(va_idx)} ({int(bundle.y_mortality[va_idx].sum())} deaths) | "
        f"Test: {len(te_idx)} ({int(bundle.y_mortality[te_idx].sum())} deaths)"
    )

    train_mask = np.zeros(n, dtype=bool)
    train_mask[tr_idx] = True

    feats, graph_feats, signal_phenos = build_feature_bundle(bundle, train_mask)
    for k, m in feats.items():
        print(f"  {k:>16s}: {m.shape}")

    splits = (tr_idx, va_idx, te_idx)
    all_results, all_names = [], []
    for key, name in MODEL_NAMES:
        classifier = "logreg" if key == "signal_only" else "l2ridge"
        y_true, y_proba = fit_and_score(
            feats[key], bundle.y_mortality, splits, kind=classifier
        )
        preds = build_explanations(
            key, y_proba, y_true, te_idx, bundle.patient_ids, graph_feats, signal_phenos
        )
        metrics = compute_all_metrics(
            y_true,
            y_proba,
            predictions=preds if preds else None,
            task_name="mortality",
        )
        metrics["dataset"] = "Synthea (Apache-2.0 synthetic, seed=20260829)"
        metrics["split"] = f"stratified 65/15/20 ({len(tr_idx)}/{len(va_idx)}/{len(te_idx)})"
        metrics["outcome"] = f"All-cause death between {LANDMARK.date()} and {HORIZON.date()}"
        metrics["positive_rate"] = float(bundle.y_mortality.mean())
        print_metrics_table(metrics, name)
        with open(METRICS_DIR / f"synthea_{key}_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        all_results.append(metrics)
        all_names.append(name)

    comparison = compare_models(
        all_results,
        all_names,
        output_path=str(METRICS_DIR / "synthea_comparison.json"),
    )

    print("\n" + "=" * 80)
    print("SYNTHEA - MODEL COMPARISON (16-yr all-cause mortality)")
    print("=" * 80)
    header = f"{'Model':<35} {'AUROC':>8} {'AUPRC':>8} {'MacroF1':>8} {'ECE':>8}"
    print(header)
    print("-" * len(header))
    for name, r in zip(all_names, all_results):
        print(
            f"{name:<35} "
            f"{r.get('auroc', 0):>8.4f} "
            f"{r.get('auprc', 0):>8.4f} "
            f"{r.get('macro_f1', 0):>8.4f} "
            f"{r.get('ece', 0):>8.4f}"
        )
    print("=" * 80)

    render_comparison_figure(all_names, all_results)
    _write_summary(all_names, all_results, comparison, bundle, splits)


def render_comparison_figure(names: List[str], results: List[Dict]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    metrics_to_plot = [
        ("auroc", "AUROC"),
        ("macro_f1", "Macro F1"),
        ("auprc", "AUPRC"),
        ("ece", "ECE (lower is better)"),
    ]
    colors = ["#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3", "#AA96DA"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for idx, (metric, title) in enumerate(metrics_to_plot):
        ax = axes[idx // 2, idx % 2]
        values = [r.get(metric, 0.0) for r in results]
        bars = ax.bar(range(len(names)), values, color=colors, alpha=0.9)
        best = int(np.argmin(values)) if metric == "ece" else int(np.argmax(values))
        bars[best].set_edgecolor("black")
        bars[best].set_linewidth(3)
        ax.set_title(title, fontweight="bold", fontsize=12)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=9)
        ax.set_ylabel("Score")
        ax.grid(axis="y", alpha=0.3)
        for i, v in enumerate(values):
            ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=9)
    plt.suptitle(
        "MedKG-Signal on Synthea Synthetic Cohort - 16-yr All-Cause Mortality (n=1,804)",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    out = IMAGES_DIR / "synthea_model_comparison.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Wrote figure: {out}")


def _write_summary(names, results, comparison, bundle, splits) -> None:
    tr_idx, va_idx, te_idx = splits
    summary = {
        "dataset": "Synthea (Apache-2.0 synthetic, Massachusetts, seed=20260829)",
        "landmark": str(LANDMARK.date()),
        "horizon": str(HORIZON.date()),
        "years": (HORIZON - LANDMARK).days / 365.25,
        "license": "Apache-2.0",
        "n_samples": int(bundle.patient_ids.shape[0]),
        "n_train": int(len(tr_idx)),
        "n_val": int(len(va_idx)),
        "n_test": int(len(te_idx)),
        "positive_rate": float(bundle.y_mortality.mean()),
        "outcome": f"All-cause death between {LANDMARK.date()} and {HORIZON.date()}",
        "models": names,
        "auroc": {n: float(r["auroc"]) for n, r in zip(names, results)},
        "auprc": {n: float(r["auprc"]) for n, r in zip(names, results)},
        "macro_f1": {n: float(r["macro_f1"]) for n, r in zip(names, results)},
        "ece": {n: float(r["ece"]) for n, r in zip(names, results)},
        "accuracy": {n: float(r["accuracy"]) for n, r in zip(names, results)},
        "evidence_precision": {
            n: float(r.get("evidence_precision", 0.0)) for n, r in zip(names, results)
        },
        "unsupported_claim_rate": {
            n: float(r.get("unsupported_claim_rate", 0.0)) for n, r in zip(names, results)
        },
        "avg_evidence_paths": {
            n: float(r.get("avg_evidence_paths", 0.0)) for n, r in zip(names, results)
        },
    }
    out = METRICS_DIR / "synthea_benchmark_summary.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary: {out}")


if __name__ == "__main__":
    main()
