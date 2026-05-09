"""Tests for cross-graph linking, navigation, and save/load persistence."""

import json
import os
import tempfile

import pytest

from veritasreason.context.context_graph import ContextGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _two_graphs():
    """Return two graphs each with one node."""
    g1 = ContextGraph()
    g2 = ContextGraph()
    g1.add_node("src", "entity", content="source entity")
    g2.add_node("dst", "entity", content="destination entity")
    return g1, g2


# ---------------------------------------------------------------------------
# link_graph / navigate_to — basic contract
# ---------------------------------------------------------------------------


class TestLinkGraph:
    def test_returns_link_id(self):
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")
        assert isinstance(link_id, str) and len(link_id) > 0

    def test_navigate_to_returns_correct_graph_and_node(self):
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")
        other, entry = g1.navigate_to(link_id)
        assert other is g2
        assert entry == "dst"

    def test_navigate_to_unknown_link_raises(self):
        g1, _ = _two_graphs()
        with pytest.raises(KeyError):
            g1.navigate_to("nonexistent-link-id")

    def test_source_not_in_graph_raises(self):
        g1, g2 = _two_graphs()
        with pytest.raises(KeyError):
            g1.link_graph(g2, "missing", "dst")

    def test_target_not_in_other_graph_raises(self):
        g1, g2 = _two_graphs()
        with pytest.raises(KeyError):
            g1.link_graph(g2, "src", "missing")

    def test_marker_node_has_cross_graph_link_type(self):
        """link_graph() must NOT pollute graph with phantom 'entity' nodes."""
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")
        marker_id = f"__cross_graph_{link_id}"
        assert marker_id in g1.nodes
        assert g1.nodes[marker_id].node_type == "cross_graph_link"

    def test_no_phantom_entity_nodes(self):
        """Only 'src' and the typed marker should exist in g1."""
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")
        entity_nodes = [n for n in g1.nodes.values() if n.node_type == "entity"]
        assert len(entity_nodes) == 1  # only 'src'

    def test_multiple_links_from_same_source(self):
        g1 = ContextGraph()
        g2 = ContextGraph()
        g3 = ContextGraph()
        g1.add_node("hub", "entity")
        g2.add_node("a", "entity")
        g3.add_node("b", "entity")
        lid1 = g1.link_graph(g2, "hub", "a")
        lid2 = g1.link_graph(g3, "hub", "b")
        other1, entry1 = g1.navigate_to(lid1)
        other2, entry2 = g1.navigate_to(lid2)
        assert other1 is g2 and entry1 == "a"
        assert other2 is g3 and entry2 == "b"


# ---------------------------------------------------------------------------
# Persistence: save_to_file / load_from_file + resolve_links
# ---------------------------------------------------------------------------


class TestCrossGraphPersistence:
    def test_graph_id_preserved_after_save_load(self):
        g1, _ = _two_graphs()
        original_id = g1.graph_id
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            g1.save_to_file(path)
            g1b = ContextGraph()
            g1b.load_from_file(path)
            assert g1b.graph_id == original_id
        finally:
            os.unlink(path)

    def test_links_section_written_to_file(self):
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            g1.save_to_file(path)
            with open(path) as fp:
                data = json.load(fp)
            assert "links" in data
            assert len(data["links"]) == 1
            lk = data["links"][0]
            assert lk["link_id"] == link_id
            assert lk["source_node_id"] == "src"
            assert lk["target_node_id"] == "dst"
            assert lk["other_graph_id"] == g2.graph_id
        finally:
            os.unlink(path)

    def test_navigate_to_raises_helpful_error_before_resolve(self):
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            g1.save_to_file(path)
            g1b = ContextGraph()
            g1b.load_from_file(path)
            with pytest.raises(KeyError, match="resolve_links"):
                g1b.navigate_to(link_id)
        finally:
            os.unlink(path)

    def test_resolve_links_restores_navigation(self):
        g1, g2 = _two_graphs()
        link_id = g1.link_graph(g2, "src", "dst")

        with (
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2,
        ):
            path1, path2 = f1.name, f2.name

        try:
            g1.save_to_file(path1)
            g2.save_to_file(path2)

            g1b = ContextGraph()
            g2b = ContextGraph()
            g1b.load_from_file(path1)
            g2b.load_from_file(path2)

            resolved = g1b.resolve_links({g2b.graph_id: g2b})
            assert resolved == 1

            other, entry = g1b.navigate_to(link_id)
            assert other is g2b
            assert entry == "dst"
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_resolve_links_returns_count(self):
        g1 = ContextGraph()
        g2 = ContextGraph()
        g3 = ContextGraph()
        g1.add_node("h", "entity")
        g2.add_node("a", "entity")
        g3.add_node("b", "entity")
        g1.link_graph(g2, "h", "a")
        g1.link_graph(g3, "h", "b")

        with (
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2,
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f3,
        ):
            p1, p2, p3 = f1.name, f2.name, f3.name
        try:
            g1.save_to_file(p1); g2.save_to_file(p2); g3.save_to_file(p3)
            g1b, g2b, g3b = ContextGraph(), ContextGraph(), ContextGraph()
            g1b.load_from_file(p1); g2b.load_from_file(p2); g3b.load_from_file(p3)
            resolved = g1b.resolve_links({g2b.graph_id: g2b, g3b.graph_id: g3b})
            assert resolved == 2
        finally:
            for p in (p1, p2, p3):
                os.unlink(p)

    def test_resolve_links_partial_registry_leaves_unresolved(self):
        """Passing only one graph to resolve_links should resolve only that link."""
        g1 = ContextGraph()
        g2 = ContextGraph()
        g3 = ContextGraph()
        g1.add_node("h", "entity")
        g2.add_node("a", "entity")
        g3.add_node("b", "entity")
        lid1 = g1.link_graph(g2, "h", "a")
        lid2 = g1.link_graph(g3, "h", "b")

        with (
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2,
            tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f3,
        ):
            p1, p2, p3 = f1.name, f2.name, f3.name
        try:
            g1.save_to_file(p1); g2.save_to_file(p2); g3.save_to_file(p3)
            g1b, g2b, g3b = ContextGraph(), ContextGraph(), ContextGraph()
            g1b.load_from_file(p1); g2b.load_from_file(p2); g3b.load_from_file(p3)

            # Only resolve g2
            resolved = g1b.resolve_links({g2b.graph_id: g2b})
            assert resolved == 1

            # lid1 navigable
            other, entry = g1b.navigate_to(lid1)
            assert other is g2b and entry == "a"

            # lid2 still unresolved — must raise with hint
            with pytest.raises(KeyError, match="resolve_links"):
                g1b.navigate_to(lid2)
        finally:
            for p in (p1, p2, p3):
                os.unlink(p)
