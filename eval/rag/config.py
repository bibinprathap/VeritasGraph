"""Typed, validated loader for ``eval/rag/config.yaml``.

The config is the single source of truth for pinned models, retrieval budgets,
seeds, and dataset paths. ``load_config`` fails fast on missing keys so a
run can never silently drift from the paper's reported setup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.yaml"


@dataclass(frozen=True)
class GenerationConfig:
    model_tag: str
    temperature: float = 0.0
    num_predict: int = 512


@dataclass(frozen=True)
class EmbeddingConfig:
    model_tag: str


@dataclass(frozen=True)
class JudgeConfig:
    model_tag: str
    temperature: float = 0.0


@dataclass(frozen=True)
class DatasetConfig:
    path: str
    limit: Optional[int] = None


@dataclass(frozen=True)
class OutputConfig:
    metrics_dir: str = "results/rag/metrics"
    tables_dir: str = "results/rag/tables"
    raw_dir: str = "results/rag/raw"


@dataclass(frozen=True)
class Config:
    seeds: List[int]
    generation: GenerationConfig
    embedding: EmbeddingConfig
    judge: JudgeConfig
    retrieval: Dict[str, Dict[str, Any]]
    datasets: Dict[str, DatasetConfig]
    output: OutputConfig = field(default_factory=OutputConfig)

    def retrieval_for(self, system: str) -> Dict[str, Any]:
        """Retrieval budget for a system; empty dict if the system has none."""
        return dict(self.retrieval.get(system, {}))


def _require(data: Dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise ValueError(f"config: missing required key {key!r} under {where}")
    return data[key]


def load_config(path: Optional[Path | str] = None) -> Config:
    """Load and validate the harness configuration."""
    cfg_path = Path(path) if path else _DEFAULT_CONFIG
    if not cfg_path.is_file():
        raise FileNotFoundError(f"config file not found: {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("config: top-level document must be a mapping")

    seeds = _require(raw, "seeds", "root")
    if not isinstance(seeds, list) or not seeds or not all(
        isinstance(s, int) for s in seeds
    ):
        raise ValueError("config: 'seeds' must be a non-empty list of ints")

    gen_raw = _require(raw, "generation", "root")
    generation = GenerationConfig(
        model_tag=str(_require(gen_raw, "model_tag", "generation")),
        temperature=float(gen_raw.get("temperature", 0.0)),
        num_predict=int(gen_raw.get("num_predict", 512)),
    )

    emb_raw = _require(raw, "embedding", "root")
    embedding = EmbeddingConfig(
        model_tag=str(_require(emb_raw, "model_tag", "embedding"))
    )

    judge_raw = _require(raw, "judge", "root")
    judge = JudgeConfig(
        model_tag=str(_require(judge_raw, "model_tag", "judge")),
        temperature=float(judge_raw.get("temperature", 0.0)),
    )

    retrieval = _require(raw, "retrieval", "root")
    if not isinstance(retrieval, dict):
        raise ValueError("config: 'retrieval' must be a mapping")

    ds_raw = _require(raw, "datasets", "root")
    if not isinstance(ds_raw, dict) or not ds_raw:
        raise ValueError("config: 'datasets' must be a non-empty mapping")
    datasets: Dict[str, DatasetConfig] = {}
    for name, spec in ds_raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"config: datasets.{name} must be a mapping")
        datasets[name] = DatasetConfig(
            path=str(_require(spec, "path", f"datasets.{name}")),
            limit=spec.get("limit"),
        )

    out_raw = raw.get("output", {}) or {}
    output = OutputConfig(
        metrics_dir=str(out_raw.get("metrics_dir", "results/rag/metrics")),
        tables_dir=str(out_raw.get("tables_dir", "results/rag/tables")),
        raw_dir=str(out_raw.get("raw_dir", "results/rag/raw")),
    )

    return Config(
        seeds=[int(s) for s in seeds],
        generation=generation,
        embedding=embedding,
        judge=judge,
        retrieval={str(k): dict(v) for k, v in retrieval.items()},
        datasets=datasets,
        output=output,
    )
