"""
Test suite for JenaStore empty graph bug fix (#257, #258).

This test suite validates the fix for the bug where JenaStore raised
'ProcessingError: Graph not initialized' when operating on empty (but initialized) graphs.

The fix replaced implicit `if not self.graph:` checks with explicit `if self.graph is None:`
checks to properly distinguish between:
- None (uninitialized graph)
- Empty graph (initialized with 0 triplets)

Contributor: @ZohaibHassan16
Issue: #257, #258
"""

import pytest
from veritasreason.triplet_store import JenaStore
from veritasreason.semantic_extract.triplet_extractor import Triplet
from veritasreason.utils.exceptions import ProcessingError


class TestJenaStoreEmptyGraph:
    """Test JenaStore operations on empty graphs."""
    
    def test_empty_graph_initialization(self):
        """Test that empty graph initializes correctly."""
        store = JenaStore()
        
        # Graph should be initialized (not None)
        assert store.graph is not None
        
        # Graph should be empty (0 triplets)
        assert len(store.graph) == 0
    
    def test_add_triplets_to_empty_graph(self):
        """Test adding triplets to empty initialized graph."""
        store = JenaStore()
        
        # Verify graph is empty
        assert len(store.graph) == 0
        
        # Add triplets to empty graph (should not raise error)
        triplets = [
            Triplet(subject="http://example.org/Alice", 
                   predicate="http://example.org/knows", 
                   object="http://example.org/Bob"),
            Triplet(subject="http://example.org/Bob", 
                   predicate="http://example.org/age", 
                   object="30")
        ]
        
        result = store.add_triplets(triplets)
        
        # Verify success
        assert result["success"] is True
        assert result["added"] == 2
        assert len(store.graph) == 2
    
    def test_get_triplets_from_empty_graph(self):
        """Test getting triplets from empty initialized graph."""
        store = JenaStore()
        
        # Verify graph is empty
        assert len(store.graph) == 0
        
        # Get triplets from empty graph (should return empty list, not error)
        triplets = store.get_triplets()
        
        # Verify returns empty list
        assert triplets == []
        assert isinstance(triplets, list)
    
    def test_get_triplets_with_filters_on_empty_graph(self):
        """Test filtered queries on empty graph."""
        store = JenaStore()
        
        # Query with subject filter
        triplets = store.get_triplets(subject="http://example.org/Alice")
        assert triplets == []
        
        # Query with predicate filter
        triplets = store.get_triplets(predicate="http://example.org/knows")
        assert triplets == []
        
        # Query with object filter
        triplets = store.get_triplets(object="http://example.org/Bob")
        assert triplets == []
        
        # Query with multiple filters
        triplets = store.get_triplets(
            subject="http://example.org/Alice",
            predicate="http://example.org/knows"
        )
        assert triplets == []
    
    def test_delete_triplet_from_empty_graph(self):
        """Test deleting triplet from empty graph."""
        store = JenaStore()
        
        # Verify graph is empty
        assert len(store.graph) == 0
        
        # Attempt to delete from empty graph (should not raise error)
        triplet = Triplet(
            subject="http://example.org/Alice",
            predicate="http://example.org/knows",
            object="http://example.org/Bob"
        )
        
        # Should succeed gracefully (nothing to delete)
        result = store.delete_triplet(triplet)
        assert result["success"] is True
        
        # Graph should still be empty
        assert len(store.graph) == 0
    
    def test_execute_sparql_on_empty_graph(self):
        """Test SPARQL execution on empty graph."""
        store = JenaStore()
        
        # Verify graph is empty
        assert len(store.graph) == 0
        
        # Execute SELECT query on empty graph
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        result = store.execute_sparql(query)
        
        # Should return empty results, not error
        assert result["success"] is True
        assert result["bindings"] == []
        assert result["variables"] == ["s", "p", "o"]
    
    def test_execute_sparql_ask_on_empty_graph(self):
        """Test SPARQL ASK query on empty graph."""
        store = JenaStore()
        
        # ASK query on empty graph
        query = "ASK WHERE { ?s ?p ?o }"
        result = store.execute_sparql(query)
        
        # Should execute without error
        assert result["success"] is True
    
    def test_execute_sparql_construct_on_empty_graph(self):
        """Test SPARQL CONSTRUCT query on empty graph."""
        store = JenaStore()
        
        # CONSTRUCT query on empty graph
        query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        result = store.execute_sparql(query)
        
        # Should execute without error
        assert result["success"] is True
    
    def test_serialize_empty_graph(self):
        """Test serialization of empty graph."""
        store = JenaStore()
        
        # Verify graph is empty
        assert len(store.graph) == 0
        
        # Serialize empty graph in Turtle format
        turtle = store.serialize(format="turtle")
        
        # Should return valid (empty) RDF, not error
        assert isinstance(turtle, str)
        # Empty graph serialization should be minimal
        assert len(turtle) < 100  # Just namespace declarations
    
    def test_serialize_empty_graph_multiple_formats(self):
        """Test serialization of empty graph in multiple formats."""
        store = JenaStore()
        
        # Turtle
        turtle = store.serialize(format="turtle")
        assert isinstance(turtle, str)
        
        # RDF/XML
        rdfxml = store.serialize(format="xml")
        assert isinstance(rdfxml, str)
        
        # N-Triples
        ntriples = store.serialize(format="nt")
        assert isinstance(ntriples, str)
    
    def test_graph_becomes_empty_after_deletion(self):
        """Test graph that becomes empty after deleting all triplets."""
        store = JenaStore()
        
        # Add a triplet
        triplet = Triplet(
            subject="http://example.org/Alice",
            predicate="http://example.org/knows",
            object="http://example.org/Bob"
        )
        store.add_triplets([triplet])
        assert len(store.graph) == 1
        
        # Delete the triplet (graph becomes empty)
        store.delete_triplet(triplet)
        assert len(store.graph) == 0
        
        # Verify operations still work on now-empty graph
        triplets = store.get_triplets()
        assert triplets == []
        
        # Add another triplet (should work)
        new_triplet = Triplet(
            subject="http://example.org/Charlie",
            predicate="http://example.org/age",
            object="25"
        )
        result = store.add_triplets([new_triplet])
        assert result["success"] is True
        assert len(store.graph) == 1
    
    def test_rapid_add_delete_operations(self):
        """Test rapid add/delete operations that oscillate between empty/non-empty."""
        store = JenaStore()
        
        triplet = Triplet(
            subject="http://example.org/Test",
            predicate="http://example.org/value",
            object="123"
        )
        
        # Oscillate 10 times
        for i in range(10):
            # Add (graph becomes non-empty)
            store.add_triplets([triplet])
            assert len(store.graph) == 1
            
            # Delete (graph becomes empty)
            store.delete_triplet(triplet)
            assert len(store.graph) == 0
            
            # Verify operations work on empty graph
            result = store.get_triplets()
            assert result == []
    
    def test_uninitialized_graph_raises_error(self):
        """Test that None (uninitialized) graph raises appropriate errors."""
        store = JenaStore()
        
        # Manually set graph to None (simulating uninitialized state)
        store.graph = None
        
        # add_triplets should raise ProcessingError
        with pytest.raises(ProcessingError, match="Graph not initialized"):
            store.add_triplets([
                Triplet(subject="s", predicate="p", object="o")
            ])
        
        # delete_triplet should raise ProcessingError
        with pytest.raises(ProcessingError, match="Graph not initialized"):
            store.delete_triplet(
                Triplet(subject="s", predicate="p", object="o")
            )
        
        # execute_sparql should raise ProcessingError
        with pytest.raises(ProcessingError, match="Graph not initialized"):
            store.execute_sparql("SELECT * WHERE { ?s ?p ?o }")
    
    def test_get_triplets_returns_empty_list_for_none_graph(self):
        """Test that get_triplets returns [] for None graph (not error)."""
        store = JenaStore()
        
        # Manually set graph to None
        store.graph = None
        
        # get_triplets should return empty list (graceful handling)
        triplets = store.get_triplets()
        assert triplets == []
    
    def test_serialize_returns_empty_string_for_none_graph(self):
        """Test that serialize returns empty string for None graph."""
        store = JenaStore()
        
        # Manually set graph to None
        store.graph = None
        
        # serialize should return empty string (graceful handling)
        result = store.serialize()
        assert result == ""
    
    def test_create_model_with_empty_graph(self):
        """Test create_model with empty graph."""
        store = JenaStore()
        
        # Verify graph is empty
        assert len(store.graph) == 0
        
        # Create model should work
        model_info = store.create_model()
        
        assert model_info["triplet_count"] == 0
        assert "model_id" in model_info
    
    def test_empty_graph_with_concurrent_operations(self):
        """Test concurrent operations on empty graph."""
        import threading
        
        store = JenaStore()
        errors = []
        
        def add_triplet():
            try:
                # Add triplet (may see other threads' triplets due to race condition)
                store.add_triplets([
                    Triplet(
                        subject=f"http://example.org/Entity{threading.current_thread().ident}",
                        predicate="http://example.org/type",
                        object="Test"
                    )
                ])
            except Exception as e:
                errors.append(e)
        
        # Run 5 concurrent threads
        threads = [threading.Thread(target=add_triplet) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # No errors should occur
        assert len(errors) == 0
        
        # Graph should have 5 triplets
        assert len(store.graph) == 5
    
    def test_benchmarking_scenario_empty_graph(self):
        """Test benchmarking scenario with fresh empty graph."""
        # This simulates the benchmarking suite use case
        store = JenaStore()
        
        # Benchmarking starts with empty graph
        assert len(store.graph) == 0
        
        # Benchmark: Add 100 triplets
        triplets = [
            Triplet(
                subject=f"http://example.org/Entity{i}",
                predicate="http://example.org/type",
                object="BenchmarkEntity"
            )
            for i in range(100)
        ]
        
        result = store.add_triplets(triplets)
        assert result["success"] is True
        assert result["added"] == 100
        
        # Benchmark: Query all
        all_triplets = store.get_triplets()
        assert len(all_triplets) == 100
        
        # Benchmark: SPARQL query
        sparql_result = store.execute_sparql("SELECT ?s WHERE { ?s ?p ?o }")
        assert sparql_result["success"] is True
        assert len(sparql_result["bindings"]) == 100


class TestJenaStoreEdgeCases:
    """Additional edge case tests for JenaStore."""
    
    def test_empty_graph_with_blank_nodes(self):
        """Test empty graph operations with blank nodes."""
        store = JenaStore()
        
        # Add triplet with blank node
        triplet = Triplet(
            subject="_:blank1",
            predicate="http://example.org/type",
            object="BlankNode"
        )
        
        result = store.add_triplets([triplet])
        assert result["success"] is True
    
    def test_empty_graph_with_very_long_uris(self):
        """Test empty graph with very long URIs (>1000 chars)."""
        store = JenaStore()
        
        long_uri = "http://example.org/" + "a" * 1000
        triplet = Triplet(
            subject=long_uri,
            predicate="http://example.org/type",
            object="LongURI"
        )
        
        result = store.add_triplets([triplet])
        assert result["success"] is True
        assert len(store.graph) == 1
    
    def test_empty_graph_with_unicode_literals(self):
        """Test empty graph with Unicode literals."""
        store = JenaStore()
        
        triplet = Triplet(
            subject="http://example.org/Entity",
            predicate="http://example.org/name",
            object="こんにちは世界"  # Japanese: Hello World
        )
        
        result = store.add_triplets([triplet])
        assert result["success"] is True
        assert len(store.graph) == 1
    
    def test_empty_graph_cleared_and_reused(self):
        """Test graph that is cleared and reused multiple times."""
        store = JenaStore()
        
        for iteration in range(3):
            # Add triplets
            triplets = [
                Triplet(
                    subject=f"http://example.org/Entity{i}",
                    predicate="http://example.org/iteration",
                    object=str(iteration)
                )
                for i in range(10)
            ]
            store.add_triplets(triplets)
            assert len(store.graph) == 10
            
            # Clear graph by deleting all
            for triplet in triplets:
                store.delete_triplet(triplet)
            
            # Verify empty
            assert len(store.graph) == 0
            
            # Verify operations work
            result = store.get_triplets()
            assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
