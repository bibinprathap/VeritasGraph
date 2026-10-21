"""Unit tests for eval.rag.config — the pinned-config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.rag import config as cfgmod


def test_load_default_config():
    cfg = cfgmod.load_config()
    assert cfg.seeds == [13, 21, 42]
    assert cfg.generation.model_tag
    assert cfg.generation.temperature == 0.0
    assert cfg.embedding.model_tag == "nomic-embed-text"
    assert cfg.judge.model_tag
    assert "hotpotqa" in cfg.datasets
    assert "behindthetech" in cfg.datasets


def test_retrieval_for_known_and_unknown_system():
    cfg = cfgmod.load_config()
    assert cfg.retrieval_for("veritasgraph")["max_depth"] == 2
    assert cfg.retrieval_for("naive")["top_k"] == 8
    assert cfg.retrieval_for("does-not-exist") == {}


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        cfgmod.load_config(tmp_path / "nope.yaml")


def test_missing_required_key_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("seeds: [1]\n", encoding="utf-8")  # missing generation/etc.
    with pytest.raises(ValueError, match="generation"):
        cfgmod.load_config(bad)


def test_bad_seeds_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "seeds: []\n"
        "generation: {model_tag: x}\n"
        "embedding: {model_tag: y}\n"
        "judge: {model_tag: z}\n"
        "retrieval: {}\n"
        "datasets: {d: {path: p}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="seeds"):
        cfgmod.load_config(bad)


def test_frozen_config_is_immutable():
    cfg = cfgmod.load_config()
    with pytest.raises(Exception):
        cfg.seeds = [1]  # type: ignore[misc]
