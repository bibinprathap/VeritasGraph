# VeritasGraph Reasoning Search Enhancement

## Inspired by PageIndex's 98.7% Accuracy Approach

This enhancement adapts key innovations from [PageIndex](https://github.com/VectifyAI/PageIndex) to improve VeritasGraph's accuracy from 99% to potentially higher levels.

## Key Concepts from PageIndex

### 1. **Reasoning-Based Retrieval** (vs. Pure Vector Similarity)
- PageIndex uses LLM reasoning to navigate document structure
- "Similarity ≠ Relevance" — what we need is **relevance through reasoning**
- VeritasGraph adaptation: LLM reasons over graph structure instead of relying solely on embeddings

### 2. **Hierarchical Tree Navigation**
- PageIndex builds a "table of contents" tree from documents
- Tree search uses LLM to decide which branches to explore
- VeritasGraph adaptation: Treat knowledge graph communities as a hierarchy, reason about which to explore

### 3. **Verification & Auto-Correction Loop**
- PageIndex verifies extracted information against source text
- Auto-corrects when accuracy falls below threshold
- VeritasGraph adaptation: Verify answers against retrieved context, auto-correct if needed

### 4. **Explicit Reasoning Traces**
- Every decision is documented with reasoning
- Provides explainability and auditability
- VeritasGraph adaptation: Track all reasoning steps for transparency

## New Search Modes in VeritasGraph

### 🎯 Reasoning Search (`query_type="reasoning"`)
The highest-accuracy mode that implements the full PageIndex-inspired pipeline:

1. **Query Analysis**: LLM analyzes the query to determine:
   - Query type (specific, broad, comparative, aggregative)
   - Key concepts and relevant entities
   - Optimal search strategy

2. **Reasoning-Based Retrieval**: Instead of pure embedding similarity:
   - LLM examines graph structure (communities, entities, relationships)
   - Makes explicit decisions about which nodes to explore
   - Documents reasoning for each choice

3. **Answer Generation**: Based on retrieved context with citations

4. **Verification & Correction**: 
   - Validates answer against context
   - Checks for hallucinations
   - Auto-corrects if accuracy is low

### 🔄 Hybrid Search (`query_type="hybrid"`)
Combines local (entity-focused) and global (community-focused) results:
- Runs both search types in parallel
- Synthesizes results using LLM reasoning
- Best for complex queries needing both detail and overview

### 🌐 Global Search (`query_type="global"`)
Standard GraphRAG community-based search for broad overviews.

### 📍 Local Search (`query_type="local"`)
Standard GraphRAG entity-focused search for specific queries.

## Technical Implementation

### ReasoningSearchEngine Class

```python
from reasoning_search import ReasoningSearchEngine

engine = ReasoningSearchEngine(
    input_dir="output/artifacts",
    community_level=2,
    temperature=0.3
)

result = await engine.search(
    query="What are student visa requirements?",
    response_type="Multiple Paragraphs"
)

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Verified: {result.verified}")
print(f"Sources: {result.sources}")
```

### Integration with Gradio UI

The new search modes are automatically available in the Gradio interface:
- Select "reasoning" or "hybrid" from the Query Type radio buttons
- Confidence scores and verification status are appended to responses
- Reasoning traces are available for debugging

## Accuracy Improvements

| Feature | Standard GraphRAG | With Reasoning Enhancement |
|---------|-------------------|----------------------------|
| Retrieval | Vector similarity | LLM reasoning + vectors |
| Validation | None | Multi-step verification |
| Correction | None | Auto-correction loop |
| Explainability | Limited | Full reasoning traces |
| Hallucination Detection | None | Built-in checking |

## Configuration Options

```python
# In app.py or reasoning_search.py

# Community level for graph navigation
community_level = 2  # Higher = more granular

# Temperature for reasoning (lower = more focused)
temperature = 0.3

# Response type
response_type = "Multiple Paragraphs"  # or "Single Paragraph", etc.
```

## API Reference

### enhanced_search()
Main entry point for reasoning-based search.

```python
result = await enhanced_search(
    query="Your question",
    input_dir="path/to/artifacts",
    query_type="auto",  # or "local", "global", "hybrid"
    community_level=2,
    temperature=0.3,
    response_type="Multiple Paragraphs"
)
```

Returns:
```python
{
    "response": "The answer...",
    "confidence": 0.95,
    "verified": True,
    "corrections_made": 0,
    "sources": [...],
    "reasoning_trace": [...]
}
```

### reasoning_local_search()
Entity-focused search with reasoning verification.

### reasoning_global_search()
Community-focused search with reasoning verification.

### hybrid_reasoning_search()
Combined local + global search with synthesis.

## Files

- `reasoning_search.py` - Main reasoning search implementation
- `test_reasoning_search.py` - Test suite
- `REASONING_SEARCH_GUIDE.md` - This documentation

## Future Improvements

1. **Multi-hop Reasoning**: Follow relationship chains for complex queries
2. **Caching**: Cache reasoning results for similar queries
3. **Fine-tuning**: Train models on domain-specific reasoning patterns
4. **Batch Verification**: Verify multiple claims in parallel
5. **Confidence Calibration**: Better probability estimates

## References

- [PageIndex Framework](https://pageindex.ai/blog/pageindex-intro)
- [FinanceBench 98.7% Accuracy](https://github.com/VectifyAI/Mafin2.5-FinanceBench)
- [GraphRAG Documentation](https://microsoft.github.io/graphrag/)
