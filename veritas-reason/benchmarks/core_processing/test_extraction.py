from unittest.mock import patch

import pytest

from veritasreason.semantic_extract.ner_extractor import Entity, NERExtractor
from veritasreason.semantic_extract.semantic_analyzer import SemanticAnalyzer


# Fixtures
@pytest.fixture
def document_batch():
    base = "The quick brown fox jumps over the lazy dog."
    docs = [
        f"{base} Variation {i}. Apple Inc released a product in 2024."
        for i in range(50)
    ]
    return docs


# Fast wrapper-only benchmark (always runs)
def test_ner_ml_wrapper_overhead(benchmark, long_text_string):
    extractor = NERExtractor(method="ml", model="en_core_web_sm")

    entity_text = "VeritasReason"
    phrase = f"{entity_text} is a knowledge graph framework. "
    medium_text = phrase * 5

    expected_entities = []
    phrase_len = len(phrase)
    for i in range(5):
        start = i * phrase_len
        end = start + len(entity_text)
        ent = Entity(
            text=entity_text,
            label="ORG",
            start_char=start,
            end_char=end,
            confidence=0.98,
            metadata={"lemma": entity_text},
        )
        expected_entities.append(ent)

    def custom_ml_extraction(text: str, **method_options):
        min_confidence = method_options.get("min_confidence", 0.5)
        entity_types = method_options.get("entity_types")
        filtered = []
        for ent in expected_entities:
            if entity_types and ent.label not in entity_types:
                continue
            if ent.confidence >= min_confidence:
                filtered.append(ent)
        return filtered

    with patch(
        "veritasreason.semantic_extract.methods.get_entity_method"
    ) as mock_get_method:
        mock_get_method.side_effect = lambda name: (
            custom_ml_extraction if name == "ml" else (lambda t, **o: [])
        )

        def op():
            return extractor.extract_entities(text=medium_text)

        result = benchmark.pedantic(op, rounds=20, iterations=5)

    assert len(result) == 5
    assert all(e.text == "VeritasReason" for e in result)
    assert all(e.label == "ORG" for e in result)
    assert all(e.confidence == 0.98 for e in result)
    assert all(medium_text[e.start_char : e.end_char] == e.text for e in result)


# Real spaCy benchmark
@pytest.mark.benchmark(group="ner_real_ml")
def test_ner_ml_real_performance(benchmark, long_text_string):
    """
    Full spaCy inference + wrapper overhead.
    Only runs when real spaCy is loaded (BENCHMARK_REAL_LIBS=1).
    """
    extractor = NERExtractor(method="ml", model="en_core_web_sm")

    if (
        extractor.nlp is None
        or not hasattr(extractor.nlp, "pipe_names")
        or "ner" not in extractor.nlp.pipe_names
    ):
        pytest.skip(
            "Real spaCy NER pipeline not available — skipping production benchmark"
        )

    medium_text = long_text_string[:10000]

    medium_text += " Apple Inc. was founded by Steve Jobs and Steve Wozniak in Cupertino, California on April 1, 1976. Microsoft is a competitor."

    def op():
        return extractor.extract_entities(text=medium_text)

    result = benchmark.pedantic(op, rounds=6, iterations=2)

    assert len(result) >= 6
    assert any("Apple" in e.text and e.label == "ORG" for e in result)
    assert any(e.label == "PERSON" for e in result)
    assert any(e.label in {"GPE", "LOC"} for e in result)
    assert any(e.label == "DATE" for e in result)
    assert any("Microsoft" in e.text and e.label == "ORG" for e in result)


def test_ner_pattern_speed(benchmark, long_text_string):
    extractor = NERExtractor(method="pattern")
    medium_text = long_text_string[:50000]
    text_with_entities = medium_text + " Apple Inc. was founded in 1976. "

    def op():
        return extractor.extract_entities(text=text_with_entities)

    result = benchmark.pedantic(op, rounds=20, iterations=5)
    assert len(result) > 0
    assert result[0].label in ["ORG", "DATE", "UNKNOWN"]


def test_ner_batch_throughput(benchmark, document_batch):
    extractor = NERExtractor(method="pattern")

    def run_batch():
        return extractor.extract_entities_batch(document_batch, max_workers=2)

    result = benchmark.pedantic(run_batch, rounds=10, iterations=5)
    assert len(result) == len(document_batch)
    assert len(result[0]) > 0


def test_similarity_calculation(benchmark):
    analyzer = SemanticAnalyzer()
    text1 = "The quick brown fox jumps over the lazy dog" * 10
    text2 = "The slow brown fox jumped over the sleeping dog" * 10

    def op():
        return analyzer.calculate_similarity(text1, text2, method="jaccard")

    result = benchmark.pedantic(op, rounds=100, iterations=100)
    assert 0.0 <= result <= 1.0


def test_clustering_algorithm(benchmark, document_batch):
    analyzer = SemanticAnalyzer()
    options = {"similarity_threshold": 0.1}

    def op():
        return analyzer.cluster_veritasreasonlly(texts=document_batch, **options)

    result = benchmark.pedantic(op, rounds=10, iterations=5)
    assert len(result) > 0
    assert result[0].texts
