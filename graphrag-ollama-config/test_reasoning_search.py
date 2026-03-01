"""
Test script for Reasoning-Based Search
Run from the graphrag-ollama-config directory
"""
import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reasoning_search import (
    enhanced_search,
    reasoning_local_search,
    reasoning_global_search,
    hybrid_reasoning_search,
    ReasoningSearchEngine
)

async def test_reasoning_search():
    """Test the reasoning-based search functionality"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "output", "artifacts")
    
    if not os.path.exists(input_dir):
        print(f"❌ Input directory not found: {input_dir}")
        print("Make sure you have run GraphRAG indexing first.")
        return
    
    print("=" * 70)
    print("🧪 Testing PageIndex-Inspired Reasoning Search for VeritasGraph")
    print("=" * 70)
    
    # Test queries
    test_queries = [
        "What are the main eligibility criteria for student visas?",
        "Compare USA F-1 and UK Tier 4 student visa requirements",
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"📝 Query: {query}")
        print("=" * 70)
        
        try:
            # Test enhanced_search with auto strategy
            print("\n🎯 Testing Reasoning Search (auto strategy)...")
            result = await enhanced_search(
                query=query,
                input_dir=input_dir,
                query_type="auto",
                community_level=2,
                temperature=0.3
            )
            
            print(f"\n✅ Response received!")
            print(f"📊 Confidence: {result.get('confidence', 'N/A'):.2%}")
            print(f"✓ Verified: {result.get('verified', 'N/A')}")
            
            # Print reasoning trace summary
            if 'reasoning_trace' in result:
                print(f"\n🔍 Reasoning Steps ({len(result['reasoning_trace'])}):")
                for i, step in enumerate(result['reasoning_trace'], 1):
                    print(f"   {i}. {step['step']}: {step.get('confidence', 0):.2%} confidence")
            
            # Print sources
            if 'sources' in result and result['sources']:
                print(f"\n📚 Sources ({len(result['sources'])}):")
                for src in result['sources'][:3]:
                    print(f"   - [{src['type']}] {src['name']}")
            
            # Print truncated response
            response = result.get('response', '')
            print(f"\n📄 Answer Preview:")
            print("-" * 50)
            if len(response) > 500:
                print(response[:500] + "...")
            else:
                print(response)
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ Reasoning Search Test Complete!")
    print("=" * 70)

async def compare_search_methods():
    """Compare standard vs reasoning search"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "output", "artifacts")
    
    if not os.path.exists(input_dir):
        print(f"❌ Input directory not found: {input_dir}")
        return
    
    query = "What financial requirements exist for student visas?"
    
    print("=" * 70)
    print("📊 Comparing Search Methods")
    print("=" * 70)
    print(f"\nQuery: {query}\n")
    
    # Test reasoning search
    print("🎯 Method 1: Reasoning Search (PageIndex-style)")
    print("-" * 50)
    try:
        result = await enhanced_search(query, input_dir, "auto", 2, 0.3)
        print(f"Confidence: {result.get('confidence', 0):.2%}")
        print(f"Verified: {result.get('verified', False)}")
        print(f"Sources: {len(result.get('sources', []))}")
        print(f"Response length: {len(result.get('response', ''))} chars")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test hybrid search
    print("\n🔄 Method 2: Hybrid Search")
    print("-" * 50)
    try:
        result = await hybrid_reasoning_search(query, input_dir, 2, 0.3)
        print(f"Confidence: {result.get('confidence', 0):.2%}")
        print(f"Strategy: {result.get('search_strategy', 'N/A')}")
        print(f"Response length: {len(result.get('response', ''))} chars")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 70)
    print("Comparison complete!")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("VeritasGraph Reasoning Search Test Suite")
    print("Based on PageIndex's 98.7% accuracy approach")
    print("=" * 70 + "\n")
    
    # Run tests
    asyncio.run(test_reasoning_search())
    
    print("\n\n")
    asyncio.run(compare_search_methods())
