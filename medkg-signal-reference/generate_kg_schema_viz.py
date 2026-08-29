"""Generate a KG schema (meta-graph) figure for the paper.

Shows the 6 node types and 6 relation types in the MedKG-Signal ontology.
Output: results/images/kg_schema.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx


NODE_TYPES = [
    ("Encounter", "#ef6b6b"),
    ("Diagnosis", "#2ec5b6"),
    ("Symptom", "#ffd166"),
    ("Medication", "#8dd7c0"),
    ("LabMarker", "#f26d6d"),
    ("SignalPhenotype", "#a78bfa"),
]

RELATIONS = [
    ("Encounter", "Diagnosis", "HAS_DIAGNOSIS"),
    ("Encounter", "Symptom", "PRESENTS_WITH"),
    ("Encounter", "Medication", "TREATED_WITH"),
    ("Encounter", "LabMarker", "MEASURED_BY"),
    ("Encounter", "SignalPhenotype", "EXHIBITS"),
    ("Diagnosis", "Symptom", "MANIFESTS_AS"),
    ("Diagnosis", "Medication", "INDICATES"),
    ("Diagnosis", "LabMarker", "MONITORED_BY"),
    ("Diagnosis", "SignalPhenotype", "CORRELATES_WITH"),
    ("SignalPhenotype", "LabMarker", "CO_OCCURS_WITH"),
]


def build_schema_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for name, color in NODE_TYPES:
        g.add_node(name, color=color)
    for src, dst, label in RELATIONS:
        g.add_edge(src, dst, label=label)
    return g


def main() -> None:
    g = build_schema_graph()
    pos = {
        "Encounter":       (0.0,  0.0),
        "Diagnosis":       (1.8,  0.7),
        "Symptom":         (1.3, -1.4),
        "Medication":      (3.0, -0.6),
        "LabMarker":       (3.4,  1.5),
        "SignalPhenotype": (0.7,  2.0),
    }

    fig, ax = plt.subplots(figsize=(11, 7.2))
    ax.set_axis_off()
    ax.set_title(
        "MedKG-Signal Knowledge Graph Schema",
        fontsize=16, fontweight="bold", pad=14,
    )

    node_colors = [g.nodes[n]["color"] for n in g.nodes]
    nx.draw_networkx_nodes(
        g, pos, ax=ax,
        node_color=node_colors,
        node_size=3600,
        edgecolors="#222",
        linewidths=1.4,
    )
    nx.draw_networkx_labels(
        g, pos, ax=ax,
        font_size=10, font_weight="bold",
    )

    # Draw each edge with a slight curve so labels are readable.
    for i, (src, dst, key) in enumerate(g.edges(keys=True)):
        label = g.edges[src, dst, key]["label"]
        rad = 0.15 if (i % 2 == 0) else -0.15
        nx.draw_networkx_edges(
            g, pos, ax=ax,
            edgelist=[(src, dst)],
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>",
            arrowsize=16,
            edge_color="#4a4a4a",
            width=1.4,
            alpha=0.85,
        )
        # Midpoint with curvature offset for the label.
        (x1, y1), (x2, y2) = pos[src], pos[dst]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # Offset perpendicular to the edge for readability.
        dx, dy = (x2 - x1), (y2 - y1)
        norm = (dx * dx + dy * dy) ** 0.5 or 1.0
        ox, oy = -dy / norm * 0.18 * (1 if rad > 0 else -1), dx / norm * 0.18 * (1 if rad > 0 else -1)
        ax.text(
            mx + ox, my + oy, label,
            fontsize=8, color="#333", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="#bbb", lw=0.6, alpha=0.85),
        )

    # Legend of node types.
    handles = [
        plt.Line2D(
            [0], [0], marker="o", color="w",
            markerfacecolor=color, markeredgecolor="#222",
            markersize=13, label=name,
        )
        for name, color in NODE_TYPES
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        frameon=True, fontsize=9,
        title="Node Types", title_fontsize=10,
    )

    out = Path(__file__).resolve().parent / "results" / "images" / "kg_schema.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
