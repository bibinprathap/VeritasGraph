"""Render all 5 research-paper diagrams as publication-quality figures (offline).

Theme: "Technical Blueprint" — a light, editorial engineering-drawing style
(warm paper background, thin ink strokes, restrained ink-on-paper palette,
serif/mono labels, numbered callouts). Deliberately NOT the dark neon
auto-generated look. Pure matplotlib so it runs with no internet, no Node,
no mermaid-cli.

Run (from the Awesome-AI4Med directory):
    /home/sijo/VeritasGraph/.venv/bin/python medtrust/diagrams.py

Outputs -> medtrust/diagrams/  (both .png and .pdf)
    diagram1_system_architecture
    diagram2_request_sequence
    diagram3_module_mapping
    diagram4_threat_model
    diagram5_results_ablation
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

OUT = os.path.join(os.path.dirname(__file__), "diagrams")

# ---------------------------------------------------------------------------
# Global typographic style — serif body, monospace for code/identifiers.
# A print/engineering-drawing feel rather than a UI-mockup feel.
# ---------------------------------------------------------------------------
_available = {f.name for f in font_manager.fontManager.ttflist}
BODY_FONT = "DejaVu Serif" if "DejaVu Serif" in _available else "serif"
MONO_FONT = "DejaVu Sans Mono"
plt.rcParams.update({
    "font.family": BODY_FONT,
    "axes.unicode_minus": False,
})

# ---------------------------------------------------------------------------
# Palette — "ink on warm paper". Muted, print-safe, no neon.
# ---------------------------------------------------------------------------
PAPER   = "#f4f1e8"   # warm off-white background
PANEL   = "#faf8f2"   # slightly lighter card fill
INK     = "#1f2328"   # near-black ink for text/strokes
SUBINK  = "#5b5f66"   # secondary grey ink
RULE    = "#c9c2ac"   # hairline rule colour

# Restrained accent inks (desaturated, editorial)
NAVY    = "#26415e"   # control / trust plane
TEAL    = "#2f6f6a"   # retrieval / data
OLIVE   = "#6c6a2f"   # observability / governance
CLARET  = "#7a3b3b"   # threat / attacker
PLUM    = "#5a4160"   # human-in-loop
SLATE   = "#3c4650"   # generic component

# Tint fills (paper-tinted, low chroma) paired with the inks above
T_NAVY   = "#dbe4ee"
T_TEAL   = "#d8e6e3"
T_OLIVE  = "#e8e6cf"
T_CLARET = "#eeddd9"
T_PLUM   = "#e5dde8"
T_SLATE  = "#e0e4e8"
T_GOLD   = "#efe6c8"


def _save(fig, name: str) -> None:
    """Save both a raster PNG and a vector PDF (publication-grade)."""
    fig.savefig(os.path.join(OUT, name + ".png"),
                facecolor=fig.get_facecolor(), bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".pdf"),
                facecolor=fig.get_facecolor(), bbox_inches="tight")


def _fig(w=13, h=8, title="", fignum="", subtitle=""):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Engineering-drawing frame: thin double border
    ax.add_patch(Rectangle((1.2, 1.2), 97.6, 97.6, fill=False,
                           linewidth=1.4, edgecolor=INK, zorder=5))
    ax.add_patch(Rectangle((2.1, 2.1), 95.8, 95.8, fill=False,
                           linewidth=0.6, edgecolor=RULE, zorder=5))

    # Title block, top-left (like a drawing-sheet header)
    if title:
        ax.text(4, 95.4, title, ha="left", va="center", color=INK,
                fontsize=15, fontweight="bold")
    if subtitle:
        ax.text(4, 91.6, subtitle, ha="left", va="center", color=SUBINK,
                fontsize=9.5, fontstyle="italic")
    if fignum:
        ax.text(96, 95.4, fignum, ha="right", va="center", color=SUBINK,
                fontsize=9.5, family=MONO_FONT)
    ax.plot([4, 96], [89.5, 89.5], color=RULE, lw=1.0, zorder=4)
    return fig, ax


def box(ax, x, y, w, h, text, fill=PANEL, edge=INK, fc=INK, fs=10, bold=False,
        radius=0.6, mono=False, lw=1.3, accent=None):
    """A crisp rectangular component. Optional left accent bar for category."""
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0.25,rounding_size={radius}",
                       linewidth=lw, edgecolor=edge, facecolor=fill, zorder=2)
    ax.add_patch(p)
    if accent is not None:
        ax.add_patch(Rectangle((x, y), 0.8, h, facecolor=accent, edgecolor="none",
                               zorder=3))
    ax.text(x + w / 2 + (0.4 if accent else 0), y + h / 2, text,
            ha="center", va="center", color=fc,
            fontsize=fs, fontweight="bold" if bold else "normal", zorder=4,
            family=MONO_FONT if mono else BODY_FONT, wrap=True)


def arrow(ax, x1, y1, x2, y2, color=INK, style="-|>", lw=1.4, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=12, color=color, lw=lw,
                        linestyle=ls, zorder=1, shrinkA=1.5, shrinkB=1.5)
    ax.add_patch(a)


def label(ax, x, y, text, color=SUBINK, fs=8.5, ha="center", style="italic",
          mono=False):
    ax.text(x, y, text, ha=ha, va="center", color=color, fontsize=fs,
            fontstyle=style, zorder=4,
            family=MONO_FONT if mono else BODY_FONT)


def callout(ax, x, y, n, color=INK):
    """Numbered circular callout marker (engineering-drawing convention)."""
    ax.add_patch(plt.Circle((x, y), 1.4, facecolor=PAPER, edgecolor=color,
                            lw=1.2, zorder=6))
    ax.text(x, y, str(n), ha="center", va="center", color=color, fontsize=8,
            fontweight="bold", zorder=7, family=MONO_FONT)


# ---------------------------------------------------------------------------
# Diagram 1 — System architecture (layered)
# ---------------------------------------------------------------------------
def diagram1():
    fig, ax = _fig(title="MedTrust Agent — System Architecture",
                   subtitle="On-premise deployment, zero external egress",
                   fignum="FIG. 1 / SHEET A")

    ax.add_patch(Rectangle((6, 11), 88, 74, fill=False, linewidth=1.3,
                           edgecolor=NAVY, linestyle=(0, (7, 3, 1, 3)), zorder=1))
    label(ax, 50, 86.5, "ZERO-TRUST BOUNDARY  ·  on-prem  ·  no external egress",
          color=NAVY, fs=9, style="normal", mono=True)

    box(ax, 38, 78, 24, 5.5, "User / IDE agent\n(clinician · safety analyst)",
        fill=T_SLATE, edge=SLATE, accent=SLATE, fs=9)

    box(ax, 34, 68.5, 32, 5.5, "IAM / Zero-Trust Gate   (iam.py)\nauthn · least-privilege · step-up",
        fill=T_NAVY, edge=NAVY, accent=NAVY, bold=True, fs=9)

    box(ax, 34, 59, 32, 5.5, "Agent Orchestrator   (agent.py)\nrouting · tool gating · escalation",
        fill=T_NAVY, edge=NAVY, accent=NAVY, bold=True, fs=9)

    py = 47
    stages = ["Guardrails", "Memory", "Knowledge\nGraph", "Headroom", "Tools", "Data Log"]
    sw = 12.5
    for i, s in enumerate(stages):
        box(ax, 8 + i * 14.5, py, sw, 6.5, s, fill=PANEL, edge=SLATE, fs=8.5)
        if i < len(stages) - 1:
            arrow(ax, 8 + i * 14.5 + sw, py + 3.2, 8 + (i + 1) * 14.5, py + 3.2,
                  color=SUBINK)
    label(ax, 50, py + 8.2, "Governed per-turn pipeline (studio_api)", fs=8.5,
          color=SUBINK)

    box(ax, 8, 30, 26, 8.5,
        "Retrieval + Grounding  (retrieval.py)\nLiterature RAG · Structured DB\nClinical KG (de-ID · ICD10/RxNorm/SNOMED)",
        fill=T_TEAL, edge=TEAL, accent=TEAL, fs=8)
    box(ax, 37, 30, 26, 8.5,
        "Governance / GRC  (governance.py)\npolicy checks · citations\ntamper-evident audit · k-anonymity",
        fill=T_GOLD, edge=OLIVE, accent=OLIVE, fs=8)
    box(ax, 66, 30, 26, 8.5,
        "Observability / SRE  (observability.py)\ntraces · spans · metrics\nsafety counters",
        fill=T_OLIVE, edge=OLIVE, accent=OLIVE, fs=8)

    box(ax, 30, 16, 40, 5.5,
        "Answer  +  [doc#chunk] citations  +  audit id",
        fill=T_TEAL, edge=TEAL, accent=TEAL, bold=True, fs=9.5)

    box(ax, 70, 68.5, 20, 5.5, "Human Reviewer\n(step-up / escalation)",
        fill=T_PLUM, edge=PLUM, accent=PLUM, fs=8.5)

    arrow(ax, 50, 78, 50, 74)
    arrow(ax, 50, 68.5, 50, 64.5)
    arrow(ax, 50, 59, 50, 53.5)
    arrow(ax, 21, 47, 21, 38.5)
    arrow(ax, 50, 47, 50, 38.5)
    arrow(ax, 79, 47, 79, 38.5)
    arrow(ax, 50, 30, 50, 21.5)
    arrow(ax, 70, 71.2, 66, 71.2, color=PLUM, style="<|-|>")
    arrow(ax, 60, 61.5, 70, 69, color=PLUM, style="-|>", ls=(0, (3, 3)))

    _save(fig, "diagram1_system_architecture")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Diagram 2 — Request sequence
# ---------------------------------------------------------------------------
def diagram2():
    fig, ax = _fig(title="Request Sequence — Zero-Trust + Governance Path",
                   subtitle="Per-request control flow: authorize \u2192 retrieve \u2192 govern \u2192 observe",
                   fignum="FIG. 2 / SHEET B")

    actors = ["User", "IAM\n(Zero-Trust)", "Agent\nOrchestrator", "Retrieval\n/ KG",
              "Governance", "Observability", "Human\nReviewer"]
    tints = [T_SLATE, T_NAVY, T_NAVY, T_TEAL, T_GOLD, T_OLIVE, T_PLUM]
    edges = [SLATE, NAVY, NAVY, TEAL, OLIVE, OLIVE, PLUM]
    xs = [8, 22, 38, 54, 68, 82, 94]
    top, bot = 80, 13
    for name, x, ti, ed in zip(actors, xs, tints, edges):
        box(ax, x - 6, 82, 12, 5.5, name, fill=ti, edge=ed, fs=8, bold=True)
        ax.plot([x, x], [bot, top], color=RULE, lw=1.0, ls=(0, (2, 2)), zorder=1)

    steps = [
        (0, 1, "request + identity + context"),
        (1, 1, "authenticate + least-privilege check"),
        (1, 6, "step-up required (high-risk)"),
        (6, 1, "approve / deny"),
        (1, 2, "authorized (scoped token)"),
        (2, 5, "start trace span"),
        (2, 3, "retrieve (lit + DB + clinical KG)"),
        (3, 2, "evidence + provenance"),
        (2, 4, "check policy + citations"),
        (4, 2, "approved + audit id  /  block+escalate"),
        (2, 5, "emit metrics (latency, safety)"),
        (2, 0, "answer + citations + audit id"),
    ]
    y = 77
    dy = 5.0
    for i, (src, dst, text) in enumerate(steps, 1):
        x1, x2 = xs[src], xs[dst]
        selfcall = src == dst
        color = INK
        if "step-up" in text or "block" in text:
            color = CLARET
        if "approved" in text or "answer" in text:
            color = TEAL
        if selfcall:
            ax.plot([x1, x1 + 4, x1 + 4, x1], [y, y, y - 2, y - 2], color=color, lw=1.2)
            arrow(ax, x1 + 1.5, y - 2, x1, y - 2, color=color)
            callout(ax, x1 - 3.4, y, i, color=color)
            label(ax, x1 + 6, y - 1, text, ha="left", fs=8, color=INK, style="normal")
        else:
            arrow(ax, x1, y, x2, y, color=color)
            midx = (x1 + x2) / 2
            callout(ax, min(x1, x2) - 2.0, y, i, color=color)
            label(ax, midx, y + 1.2, text, fs=8, color=INK, style="normal")
        y -= dy

    _save(fig, "diagram2_request_sequence")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Diagram 3 — Module <-> VeritasGraph mapping
# ---------------------------------------------------------------------------
def diagram3():
    fig, ax = _fig(title="Reuse Mapping — medtrust/ modules \u2194 VeritasGraph stack",
                   subtitle="Each reference layer maps to a production engine",
                   fignum="FIG. 3 / SHEET C")

    left = [
        ("iam.py", 72),
        ("governance.py", 59),
        ("retrieval.py", 46),
        ("observability.py", 33),
        ("agent.py", 20),
    ]
    right = [
        ("veritasgraph_mcp/\nair-gapped · zero egress", 72),
        ("veritas-reason/\ndecision ledger · PROV-O · SoD rules", 59),
        ("studio_api/graphrag_engine.py\n+ clinical-kg/ + medkg-signal-reference/", 46),
        ("future-agi/\nOTel traces · evals · guardrails", 33),
        ("studio_api/ + demos/agent-studio/\ngoverned pipeline", 20),
    ]
    label(ax, 20, 83, "medtrust/  reference integration layer", color=NAVY,
          fs=10.5, style="normal", mono=True)
    label(ax, 74, 83, "VeritasGraph folders  ·  production engines",
          color=TEAL, fs=10.5, style="normal", mono=True)
    ax.plot([8, 32], [80.5, 80.5], color=NAVY, lw=1.0)
    ax.plot([52, 92], [80.5, 80.5], color=TEAL, lw=1.0)

    for (lt, ly), (rt, ry) in zip(left, right):
        box(ax, 8, ly, 24, 8.5, lt, fill=T_NAVY, edge=NAVY, accent=NAVY,
            bold=True, fs=9.5, mono=True)
        box(ax, 52, ry, 40, 8.5, rt, fill=T_TEAL, edge=TEAL, accent=TEAL, fs=8.5)
        arrow(ax, 32, ly + 4.25, 52, ry + 4.25, color=INK, lw=1.5)

    _save(fig, "diagram3_module_mapping")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Diagram 4 — Threat model / trust boundary
# ---------------------------------------------------------------------------
def diagram4():
    fig, ax = _fig(title="Threat Model & Trust Boundary",
                   subtitle="Adversary action \u2192 enforced control at the zero-trust boundary",
                   fignum="FIG. 4 / SHEET D")

    ax.add_patch(Rectangle((40, 11), 54, 74, fill=False, linewidth=1.3,
                           edgecolor=NAVY, linestyle=(0, (7, 3, 1, 3)), zorder=1))
    label(ax, 67, 86.5, "ZERO-TRUST BOUNDARY (on-prem)", color=NAVY, fs=9,
          style="normal", mono=True)

    box(ax, 58, 75, 30, 6.5, "Protected assets\nPHI · trials · safety data",
        fill=T_NAVY, edge=NAVY, accent=NAVY, bold=True, fs=8.5)

    threats = [
        ("Prompt injection\n(override policy / reveal prompt)", 62, "Guardrails +\nGovernance blocklist"),
        ("Data exfiltration\n(PHI / restricted trial data)", 47, "IAM least-privilege +\nk-anonymity"),
        ("Privilege escalation\n(restricted tools / role switch)", 32, "Step-up authorization +\ntool gating"),
        ("Audit tampering\n(cover tracks)", 17, "Hash-chained\naudit log (verify)"),
    ]
    for i, (name, y, control) in enumerate(threats, 1):
        box(ax, 4, y, 30, 9.5, name, fill=T_CLARET, edge=CLARET, accent=CLARET, fs=8.5)
        box(ax, 58, y, 30, 9.5, control, fill=T_TEAL, edge=TEAL, accent=TEAL, fs=8.5)
        arrow(ax, 34, y + 4.75, 58, y + 4.75, color=INK, lw=1.5)
        callout(ax, 46, y + 4.75, i, color=CLARET)
        label(ax, 46, y + 7.4, "blocked by", fs=7.5, color=SUBINK, style="italic")

    _save(fig, "diagram4_threat_model")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Diagram 5 — Results / ablation (grouped bars)
# ---------------------------------------------------------------------------
def diagram5():
    """Ablation from MEASURED results (medtrust/results/metrics.json) with 95% CI error bars."""
    import json
    import numpy as np

    metrics_path = os.path.join(os.path.dirname(__file__), "results", "metrics.json")
    if not os.path.exists(metrics_path):
        raise SystemExit(
            "results/metrics.json not found. Run: "
            "python -m medtrust.benchmark --trials 30 --seed 7"
        )
    with open(metrics_path) as f:
        data = json.load(f)

    order = ["B0", "B1", "B2", "B3", "MT"]
    cfgs = data["configs"]
    variants, acc, acc_e, hal, hal_e, cite, cite_e, blk, blk_e = ([] for _ in range(9))
    for k in order:
        m = cfgs[k]["metrics"]
        variants.append(cfgs[k]["label"].replace(" (", "\n(").replace(" ", "\n", 1))
        acc.append(m["accuracy"]["mean"]);            acc_e.append(m["accuracy"]["ci95"])
        hal.append(m["hallucination"]["mean"]);       hal_e.append(m["hallucination"]["ci95"])
        cite.append(m["citations_enforced"]["mean"]); cite_e.append(m["citations_enforced"]["ci95"])
        blk.append(m["unauthorized_blocked"]["mean"]);blk_e.append(m["unauthorized_blocked"]["ci95"])

    x = np.arange(len(variants))
    w = 0.2
    ecfg = dict(capsize=3, ecolor=INK, elinewidth=1.0)

    fig, ax = plt.subplots(figsize=(13, 7.5), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PANEL)

    bars = [
        (acc,  acc_e,  TEAL,   "Task accuracy \u2191",               "///"),
        (hal,  hal_e,  CLARET, "Hallucination rate \u2193",          "\\\\\\"),
        (cite, cite_e, OLIVE,  "Citations enforced \u2191",          "..."),
        (blk,  blk_e,  NAVY,   "Unauthorized access blocked \u2191", "xxx"),
    ]
    for i, (vals, errs, col, lab, hatch) in enumerate(bars):
        off = (i - 1.5) * w
        ax.bar(x + off, vals, w, yerr=errs, error_kw=ecfg, label=lab,
               color=col, edgecolor=INK, linewidth=0.8, hatch=hatch, alpha=0.92)

    n = data["trials"]
    ax.set_title(f"Ablation (measured, n={n} trials, 95% CI): controls vs. answer quality",
                 color=INK, fontsize=15, fontweight="bold", pad=16, family=BODY_FONT)
    ax.set_xticks(x)
    ax.set_xticklabels(variants, color=INK, fontsize=10.5)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Rate (0\u20131)", color=INK, fontsize=12)
    ax.tick_params(colors=SUBINK)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK)
    ax.grid(axis="y", color=RULE, linewidth=0.7)
    ax.set_axisbelow(True)
    leg = ax.legend(loc="upper left", facecolor=PANEL, edgecolor=RULE, fontsize=10)
    for t in leg.get_texts():
        t.set_color(INK)
    ax.text(0.5, -0.16,
            "Security/governance metrics MEASURED from real control-plane code; answer-quality metrics from documented seeded model. "
            "Governance+zero-trust add ~2% latency over B3.",
            transform=ax.transAxes, ha="center", color=SUBINK, fontsize=8.5,
            fontstyle="italic")

    _save(fig, "diagram5_results_ablation")
    plt.close(fig)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    diagram1()
    diagram2()
    diagram3()
    diagram4()
    diagram5()
    print("Diagrams written to:", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  -", f)


if __name__ == "__main__":
    main()
