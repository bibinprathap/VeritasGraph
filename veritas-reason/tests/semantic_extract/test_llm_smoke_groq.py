import os

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

pytest.importorskip("groq")

from veritasreason.semantic_extract.ner_extractor import NERExtractor
from veritasreason.semantic_extract.relation_extractor import RelationExtractor
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor


def test_groq_llm_smoke_entities_relations_triplets():
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY is not set")

    text = (
        "Apple acquired Beats in 2014 for $3 billion. "
        "Steve Jobs founded Apple. "
        "Beats is based in California."
    )
    model = "llama-3.3-70b-versatile"

    entities = NERExtractor(method="llm").extract(
        text,
        provider="groq",
        model=model,
        temperature=0.0,
        max_tokens=250,
    )
    assert isinstance(entities, list)
    assert len(entities) > 0
    assert len(entities) <= 30

    relations = RelationExtractor(method="llm").extract(
        text,
        entities=entities,
        provider="groq",
        model=model,
        temperature=0.0,
        max_tokens=350,
        max_entities_prompt=12,
    )
    assert isinstance(relations, list)
    assert len(relations) <= 30

    triplets = TripletExtractor(method="llm").extract(
        text,
        entities=entities,
        relations=relations,
        provider="groq",
        model=model,
        temperature=0.0,
        max_tokens=350,
    )
    assert isinstance(triplets, list)
    assert len(triplets) <= 40
