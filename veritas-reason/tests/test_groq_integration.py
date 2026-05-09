
import os
import sys
import json
from pprint import pprint

# Ensure the package is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritasreason.semantic_extract.methods import (
    extract_entities_llm, 
    extract_relations_llm, 
    extract_triplets_llm
)
from veritasreason.semantic_extract.providers import create_provider
from veritasreason.utils.exceptions import ProcessingError

# Set the API key
# Set the API key from environment
# We recommend setting it as an environment variable GROQ_API_KEY
if not os.environ.get("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY not set. Test will likely fail.")

def test_groq_all():
    text = "Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976. It is headquartered in Cupertino, California. The company designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories."
    
    print("--- Testing Groq Provider Availability ---")
    try:
        provider = create_provider("groq")
        available = provider.is_available()
        print(f"Groq Available: {available}")
        if not available:
            print("Error: Groq is not available. Check library installation or API key.")
            return
    except Exception as e:
        print(f"Error checking provider: {e}")
        return

    print("\n--- Testing Entity Extraction ---")
    try:
        entities = extract_entities_llm(text, provider="groq", model="llama-3.3-70b-versatile")
        print(f"Extracted {len(entities)} entities:")
        pprint(entities)
    except Exception as e:
        print(f"Entity extraction failed: {e}")

    print("\n--- Testing Relation Extraction ---")
    try:
        # Use a few entities for relation extraction
        from veritasreason.semantic_extract.models import Entity
        sample_entities = [
            Entity(name="Apple Inc.", type="ORGANIZATION"),
            Entity(name="Steve Jobs", type="PERSON")
        ]
        relations = extract_relations_llm(text, entities=sample_entities, provider="groq", model="llama-3.3-70b-versatile")
        print(f"Extracted {len(relations)} relations:")
        pprint(relations)
    except Exception as e:
        print(f"Relation extraction failed: {e}")

    print("\n--- Testing Triplet Extraction ---")
    try:
        triplets = extract_triplets_llm(text, provider="groq", model="llama-3.3-70b-versatile")
        print(f"Extracted {len(triplets)} triplets:")
        pprint(triplets)
    except Exception as e:
        print(f"Triplet extraction failed: {e}")

    print("\n--- Testing Auto-Chunking ---")
    long_text = " ".join([text] * 10) # Roughly 1000-1500 tokens
    try:
        entities_chunked = extract_entities_llm(
            long_text, 
            provider="groq", 
            model="llama-3.3-70b-versatile",
            max_text_length=200 # Force chunking
        )
        print(f"Extracted {len(entities_chunked)} entities from long text (chunked):")
        # Just show count to avoid clutter
    except Exception as e:
        print(f"Chunked extraction failed: {e}")

if __name__ == "__main__":
    test_groq_all()
