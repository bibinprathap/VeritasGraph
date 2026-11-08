"""Integration smoke tests for eval.rag.run — offline, mocked LLM.

* ``--dry-run`` enumerates every (system x task x seed) cell with no LLM calls.
* A tiny real run (limit=1) with a fake chat produces a JSON with all metric
  keys, written to a temp metrics dir.

The ollama-marked test exercises the real Ollama path and only runs locally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

from eval.rag import run as run_mod
from eval.rag.config import load_config

pytestmark = pytest.mark.usefixtures("tmp_path")


# --------------------------------------------------------------------------- #
# Fake chat
# --------------------------------------------------------------------------- #
def fake_chat(model: str, messages: List[Dict[str, str]], temperature: float) -> str:
    user = messages[-1]["content"]
    # Cite the first source id mentioned in the prompt so citation metrics are
    # non-trivial, and answer with a fixed string so EM/F1 are deterministic.
    import re

    m = re.search(r"\[([A-Za-z0-9_#:.]+)\]", user)
    cited = f"[{m.group(1)}]" if m else ""
    return f"1987 {cited}".strip() or "1987"


# --------------------------------------------------------------------------- #
# Fixtures: a mini config pointing at the test fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture()
def mini_config(tmp_path: Path) -> Path:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "seeds: [13]\n"
        "generation: {model_tag: fake-model, temperature: 0.0}\n"
        "embedding: {model_tag: fake-embed}\n"
        "judge: {model_tag: fake-judge, temperature: 0.0}\n"
        "retrieval:\n"
        "  naive: {top_k: 2}\n"
        "  veritasgraph: {max_depth: 2, max_nodes: 25}\n"
        "  msrag: {commit: fake, search: global}\n"
        "datasets:\n"
        "  hotpotqa: {path: hotpot_mini.json, limit: 2}\n"
        "  behindthetech: {path: behindthetech_mini.json, limit: null}\n"
        "output:\n"
        "  metrics_dir: metrics\n"
        "  tables_dir: tables\n"
        "  raw_dir: raw\n",
        encoding="utf-8",
    )
    return cfg_path


@pytest.fixture()
def data_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


# --------------------------------------------------------------------------- #
# Dry run
# --------------------------------------------------------------------------- #
def test_dry_run_enumerates_all_cells(mini_config: Path, data_root: Path, capsys):
    rc = run_mod.main(
        ["--task", "all", "--systems", "all", "--config", str(mini_config),
         "--data-root", str(data_root), "--dry-run"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    for system in ("naive", "msrag", "veritasgraph"):
        assert f"hotpotqa__{system}__seed13" in out
        assert f"behindthetech__{system}__seed13" in out
    # Dry run must not write any metrics files.
    assert not (data_root / "metrics").exists()


def test_dry_run_respects_system_filter(mini_config: Path, data_root: Path, capsys):
    rc = run_mod.main(
        ["--task", "hotpotqa", "--systems", "veritasgraph",
         "--config", str(mini_config), "--data-root", str(data_root), "--dry-run"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "hotpotqa__veritasgraph__seed13" in out
    assert "hotpotqa__naive" not in out


def test_dry_run_no_hypothesized_placeholder(mini_config: Path, data_root: Path, capsys):
    """Gate from the plan §7.4: dry-run output contains no 'Hypothesized' text."""
    run_mod.main(
        ["--task", "all", "--systems", "all", "--config", str(mini_config),
         "--data-root", str(data_root), "--dry-run"]
    )
    assert "hypothe" not in capsys.readouterr().out.lower()


# --------------------------------------------------------------------------- #
# Tiny real run (mocked LLM)
# --------------------------------------------------------------------------- #
def test_tiny_run_writes_metrics_json(
    mini_config: Path, data_root: Path, tmp_path: Path, monkeypatch
):
    # Point the naive adapter's chat at the fake; veritasgraph/msrag adapters
    # need engines we don't have offline, so run only the naive system here.
    monkeypatch.setattr(run_mod, "_build_naive_index_hotpot",
                        run_mod._build_naive_index_hotpot)  # no-op, clarity

    cfg = load_config(mini_config)
    result = run_mod._run_hotpotqa(
        cfg, "naive", 13, dry_run=False, limit_override=2,
        chat=fake_chat, data_root=data_root,
    )
    assert result["task"] == "hotpotqa"
    assert result["system"] == "naive"
    assert result["seed"] == 13
    assert result["n"] == 2
    for key in ("em", "f1", "cit_p", "cit_r", "cit_f1", "cit_faith"):
        assert key in result["metrics"]
        assert 0.0 <= result["metrics"][key]["mean"] <= 1.0
    assert len(result["per_query"]) == 2


def test_tiny_qfs_run_writes_metrics_json(mini_config: Path, data_root: Path):
    cfg = load_config(mini_config)
    result = run_mod._run_behindthetech(
        cfg, "naive", 13, dry_run=False, limit_override=None,
        chat=fake_chat, data_root=data_root,
    )
    assert result["task"] == "behindthetech"
    assert result["n"] == len(result["per_query"])
    for key in ("comprehensiveness", "diversity"):
        assert key in result["metrics"]
        assert 0.0 <= result["metrics"][key]["mean"] <= 1.0


def test_end_to_end_cli_run_writes_file(
    mini_config: Path, data_root: Path, tmp_path: Path, monkeypatch
):
    # Run from tmp_path so the metrics land in tmp_path/metrics.
    monkeypatch.chdir(tmp_path)
    # Copy the fixture data next to the config-relative path.
    fixtures = data_root
    (tmp_path / "hotpot_mini.json").write_text(
        (fixtures / "hotpot_mini.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "behindthetech_mini.json").write_text(
        (fixtures / "behindthetech_mini.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # Patch the config's dataset paths to be relative to cwd.
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(mini_config.read_text(encoding="utf-8"), encoding="utf-8")

    # Only naive runs offline; msrag/veritasgraph need live backends.
    rc = run_mod.main(
        ["--task", "hotpotqa", "--systems", "naive", "--config", str(cfg_path),
         "--data-root", str(tmp_path)],
        chat_fn=fake_chat,
    )
    assert rc == 0
    out_file = tmp_path / "metrics" / "hotpotqa__naive__seed13.json"
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["task"] == "hotpotqa"
    assert data["config_hash"]
    assert data["commit"]
    assert data["timestamp"]
    for key in ("em", "f1", "cit_p", "cit_r", "cit_f1", "cit_faith"):
        assert key in data["metrics"]


# --------------------------------------------------------------------------- #
# Real Ollama smoke (opt-in)
# --------------------------------------------------------------------------- #
@pytest.mark.ollama
def test_real_ollama_smoke(mini_config: Path, data_root: Path):
    """One real query against a live Ollama. Run manually: pytest -m ollama."""
    import os

    import httpx

    from eval.rag.llm import _ollama_base, ollama_chat

    # Probe the server and the model separately: a chat to a non-existent model
    # fails even when Ollama is up, which would silently skip this test forever.
    model = os.environ.get("RAG_OLLAMA_MODEL", "qwen3:8b")
    try:
        tags = httpx.get(f"{_ollama_base()}/api/tags", timeout=5.0).json()
    except Exception:
        pytest.skip("no live Ollama server available")
    if model not in {m["name"] for m in tags.get("models", [])}:
        pytest.skip(f"Ollama model {model!r} not installed (set RAG_OLLAMA_MODEL)")

    mini_config.write_text(
        mini_config.read_text(encoding="utf-8")
        .replace("fake-model", model)
        .replace("fake-judge", model),
        encoding="utf-8",
    )
    cfg = load_config(mini_config)
    result = run_mod._run_hotpotqa(
        cfg, "naive", 13, dry_run=False, limit_override=1,
        chat=ollama_chat, data_root=data_root,
    )
    assert result["n"] == 1
    assert "em" in result["metrics"]