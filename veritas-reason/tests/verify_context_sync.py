import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from veritasreason.context import AgentContext, ContextGraph

pytestmark = pytest.mark.integration

@dataclass
class VectorSearchResult:
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]

class MockVectorStore:
    def __init__(self):
        self.items: Dict[str, Any] = {}
        
    def add(self, items: List[Any]) -> List[str]:
        ids = []
        for item in items:
            # Simple ID generation if not present
            if not item.memory_id:
                item.memory_id = f"mem_{len(self.items)}"
            self.items[item.memory_id] = item
            ids.append(item.memory_id)
        print(f"MockVectorStore: Added {len(ids)} items")
        return ids
        
    def search(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        print(f"MockVectorStore: Searching for '{query}'")
        results = []
        # Simple keyword match simulation
        query_terms = query.lower().split()
        for item in self.items.values():
            if any(term in item.content.lower() for term in query_terms):
                results.append(VectorSearchResult(
                    id=item.memory_id,
                    content=item.content,
                    score=0.8,
                    metadata=item.metadata
                ))
        return results[:limit]
        
    def delete(self, ids: List[str]) -> bool:
        count = 0
        for mid in ids:
            if mid in self.items:
                del self.items[mid]
                count += 1
        return count > 0

def test_synchronous_context():
    print("--- Testing Synchronous Context Module ---")
    
    # 1. Initialize Components
    vs = MockVectorStore()
    kg = ContextGraph()
    
    context = AgentContext(vector_store=vs, knowledge_graph=kg)
    print("AgentContext initialized successfully")
    
    # 2. Store Memory
    print("\n--- Testing Store ---")
    mem_id = context.store(
        "Python is a popular programming language.", 
        conversation_id="test_conv",
        extract_entities=True
    )
    print(f"Stored memory with ID: {mem_id}")
    
    # 3. Store Documents (with graph update)
    print("\n--- Testing Document Store with Graph ---")
    docs = [
        {
            "content": "Machine learning uses Python heavily.",
            "entities": [
                {"text": "Machine learning", "type": "CONCEPT"},
                {"text": "Python", "type": "TOOL"}
            ],
            "relationships": [
                {"source": "Machine learning", "target": "Python", "type": "uses"}
            ]
        },
        {
            "content": "TensorFlow is a Python library for ML.",
            "entities": [
                {"text": "TensorFlow", "type": "TOOL"},
                {"text": "Python", "type": "TOOL"},
                {"text": "ML", "type": "CONCEPT"}
            ],
            "relationships": [
                {"source": "TensorFlow", "target": "Python", "type": "based_on"}
            ]
        }
    ]
    stats = context.store(
        docs, 
        extract_entities=True,
        link_entities=True
    )
    print(f"Stored documents stats: {stats}")
    
    # 4. Verify Graph
    print("\n--- Verifying Graph ---")
    graph_stats = kg.stats()
    print(f"Graph stats: {graph_stats}")
    if graph_stats["node_count"] > 0:
        print("SUCCESS: Graph nodes created")
    else:
        print("WARNING: No graph nodes created (expected if entity extraction is mocked/empty)")

    # 5. Retrieve
    print("\n--- Testing Retrieval ---")
    results = context.retrieve("Python", max_results=5)
    print(f"Retrieved {len(results)} results")
    for r in results:
        print(f"- {r['content']} (Score: {r['score']})")

    # 6. Test Short-Term Memory
    print("\n--- Testing Short-Term Memory (Hierarchical) ---")
    st_id = context.store(
        "This is a fleeting thought.", 
        skip_vector=True
    )
    print(f"Stored short-term only memory: {st_id}")
    
    # Verify it's not in vector store (mock check)
    is_in_vector = any("fleeting" in item.content for item in vs.items.values())
    print(f"Is in vector store: {is_in_vector} (Expected: False)")
    
    # Retrieve it (should come from short-term buffer)
    st_results = context.retrieve("fleeting thought")
    print(f"Retrieved {len(st_results)} results for short-term query")
    for r in st_results:
        source_note = f" [Source: {r.get('source', 'unknown')}]" if 'source' in r else ""
        print(f"- {r['content']} (Score: {r['score']}){source_note}")

    # 7. Test Token Management
    print("\n--- Testing Token Management ---")
    # Initialize a new memory with small token limit
    from veritasreason.context import AgentMemory
    
    # Create isolated memory instance for testing
    token_memory = AgentMemory(
        vector_store=vs, 
        token_limit=10,  # Small limit (~40 chars)
        short_term_limit=5 # Count limit
    )
    
    token_memory.store("First small item", skip_vector=True) # ~16 chars = 4 tokens
    token_memory.store("Second small item", skip_vector=True) # ~17 chars = 4 tokens
    # Total ~8 tokens. Limit 10. Should fit.
    print(f"Items after 2 small: {len(token_memory.short_term_memory)}")
    
    token_memory.store("Third small item", skip_vector=True) # ~16 chars = 4 tokens
    # Total ~12 tokens. Limit 10. Should prune oldest ("First small item").
    print(f"Items after 3rd small: {len(token_memory.short_term_memory)}")
    remaining = [m.content for m in token_memory.short_term_memory]
    print(f"Remaining items: {remaining}")
    
    if len(token_memory.short_term_memory) == 2 and remaining[0] == "Second small item":
        print("SUCCESS: Token pruning worked")
    else:
        print(f"FAILURE: Token pruning failed. Items: {len(token_memory.short_term_memory)}")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    try:
        test_synchronous_context()
    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
