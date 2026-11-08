"""Unit tests for eval.rag.report — table generation guards principle #1.

A table cell must never be emitted without a backing committed JSON; missing
cells render as explicit ``n/a (missing ...)`` placeholders, never numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.rag import report


def _blob(task: str, system: str, seed: int, metric_means: dict) -> dict:
    return {
        "task": task,
        "system": system,
        "seed": seed,
        "n": 3,
        "metrics": {k: {"mean": v, "std": 0.0, "n": 3} for k, v in metric_means.items()},
    }


def _write_metrics(metrics_dir: Path, blob: dict) -> None:
    metrics_dir.mkdir(parents=True, exist_ok=True)
    name = f"{blob['task']}__{blob['system']}__seed{blob['seed']}.json"
    (metrics_dir / name).write_text(json.dumps(blob), encoding="utf-8")


def test_load_metrics_keys(tmp_path: Path):
    _write_metrics(tmp_path, _blob("hotpotqa", "naive", 13, {"em": 0.5}))
    _write_metrics(tmp_path, _blob("hotpotqa", "naive", 42, {"em": 0.7}))
    loaded = report.load_metrics(tmp_path)
    assert set(loaded) == {("hotpotqa", "naive", 13), ("hotpotqa", "naive", 42)}


def test_mean_over_seeds():
    blobs = [
        _blob("hotpotqa", "naive", 13, {"em": 0.5}),
        _blob("hotpotqa", "naive", 42, {"em": 0.7}),
    ]
    agg = report._mean_over_seeds(blobs, "em")
    assert agg is not None
    mean, std = agg
    assert mean == 0.6
    assert std > 0.0


def test_mean_over_seeds_missing_metric_returns_none():
    blobs = [_blob("hotpotqa", "naive", 13, {"em": 0.5})]
    assert report._mean_over_seeds(blobs, "cit_faith") is None


def test_missing_cell_is_na_not_fabricated(tmp_path: Path):
    # Only naive has data; msrag/veritasgraph cells must be explicit n/a.
    _write_metrics(tmp_path, _blob("hotpotqa", "naive", 13, {"em": 0.5, "f1": 0.6}))
    md = report.render_table("hotpotqa", report.load_metrics(tmp_path), tmp_path)
    assert "Naive RAG" in md
    assert "0.500 ± 0.000" in md
    assert "n/a (missing" in md
    # No fabricated numbers for the missing systems.
    assert "MSRAG" in md and "VeritasGraph" in md


def test_best_cell_is_bolded(tmp_path: Path):
    _write_metrics(tmp_path, _blob("hotpotqa", "naive", 13, {"em": 0.5}))
    _write_metrics(tmp_path, _blob("hotpotqa", "veritasgraph", 13, {"em": 0.9}))
    md = report.render_table("hotpotqa", report.load_metrics(tmp_path), tmp_path)
    assert "**0.900 ± 0.000**" in md
    assert "**0.500" not in md


def test_generate_all_writes_tables(tmp_path: Path):
    _write_metrics(tmp_path, _blob("hotpotqa", "naive", 13, {"em": 0.5, "f1": 0.6,
                                              "cit_p": 0.4, "cit_r": 0.5,
                                              "cit_f1": 0.44, "cit_faith": 0.8}))
    _write_metrics(tmp_path, _blob("behindthetech", "naive", 13,
                                   {"comprehensiveness": 0.7, "diversity": 0.6}))
    tables = tmp_path / "tables"
    written = report.generate_all(tmp_path, tables)
    names = {p.name for p in written}
    assert names == {"table_iv.md", "table_iii.md"}
    iv = (tables / "table_iv.md").read_text(encoding="utf-8")
    iii = (tables / "table_iii.md").read_text(encoding="utf-8")
    assert "Token-F1" in iv and "Cit. Faithfulness" in iv
    assert "Comprehensiveness" in iii and "Diversity" in iii


def test_corrupt_json_is_skipped(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    loaded = report.load_metrics(tmp_path)
    assert loaded == {}
