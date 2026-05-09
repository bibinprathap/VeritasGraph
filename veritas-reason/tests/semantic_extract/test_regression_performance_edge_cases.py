import multiprocessing
import time
from unittest.mock import MagicMock, patch

import pytest

from veritasreason.semantic_extract.config import resolve_max_workers
from veritasreason.semantic_extract.ner_extractor import Entity, NERExtractor
from veritasreason.semantic_extract.relation_extractor import RelationExtractor
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor
from veritasreason.semantic_extract.semantic_network_extractor import SemanticNetworkExtractor
from veritasreason.semantic_extract.methods import filter_entities_for_text
from veritasreason.semantic_extract.schemas import RelationsResponse, RelationOut


def test_resolve_max_workers_defaults_and_clamps():
    cpu_count = multiprocessing.cpu_count() or 1

    assert resolve_max_workers(explicit=0) == 1
    assert resolve_max_workers(explicit=-10) == 1
    assert resolve_max_workers(explicit=1) == 1
    assert resolve_max_workers(explicit=10**9) == min(cpu_count, 32)

    assert resolve_max_workers(explicit=None, methods=["ml"]) == 1


def test_filter_entities_for_text_keeps_short_tokens():
    text = "US AI lab in NY"
    entities = [
        Entity(text="US", label="GPE", start_char=0, end_char=2, confidence=1.0),
        Entity(text="AI", label="TECH", start_char=3, end_char=5, confidence=1.0),
        Entity(text="NY", label="GPE", start_char=13, end_char=15, confidence=1.0),
    ]
    kept = filter_entities_for_text(text, entities, max_keep=2)
    kept_texts = {e.text for e in kept}
    assert "US" in kept_texts or "AI" in kept_texts or "NY" in kept_texts


def test_pattern_batch_defaults_to_single_worker_low_latency():
    extractor = NERExtractor(method="pattern")
    texts = [f"Text {i}" for i in range(8)]
    extractor.extract(texts)


def test_relation_llm_prompt_filter_does_not_break_mapping():
    entities = [Entity(text=f"VeryLongEntityName{i}", label="ORG", start_char=0, end_char=1, confidence=1.0) for i in range(120)]
    ghost = Entity(text="Ghost", label="ORG", start_char=0, end_char=1, confidence=1.0)
    entities.append(ghost)

    captured = {}

    class FakeLLM:
        def is_available(self):
            return True

        def generate_typed(self, prompt, schema, **kwargs):
            captured["prompt"] = prompt
            return RelationsResponse(
                relations=[
                    RelationOut(subject="Ghost", predicate="related_to", object="VeryLongEntityName0", confidence=0.9)
                ]
            )

    with patch("veritasreason.semantic_extract.methods.create_provider", return_value=FakeLLM()):
        from veritasreason.semantic_extract.methods import extract_relations_llm

        relations = extract_relations_llm(
            "Short text mentioning VeryLongEntityName0 only.",
            entities=entities,
            provider="openai",
            model="gpt-4",
            max_entities_prompt=20,
        )

    assert "Ghost" not in captured["prompt"]
    assert len(relations) == 1
    assert relations[0].subject.text == "Ghost"


def test_triplet_extractor_reuses_sub_extractors():
    ner_instance = MagicMock()
    ner_instance.extract_entities.return_value = [
        Entity(text="A", label="PERSON", start_char=0, end_char=1, confidence=1.0)
    ]

    rel_instance = MagicMock()
    rel_instance.extract_relations.return_value = []

    ner_ctor = MagicMock(return_value=ner_instance)
    rel_ctor = MagicMock(return_value=rel_instance)

    with patch("veritasreason.semantic_extract.ner_extractor.NERExtractor", ner_ctor), patch(
        "veritasreason.semantic_extract.relation_extractor.RelationExtractor", rel_ctor
    ), patch("veritasreason.semantic_extract.methods.get_triplet_method", return_value=lambda *args, **kwargs: []):
        extractor = TripletExtractor(method="pattern")
        extractor.extract_triplets("A text.")
        extractor.extract_triplets("A text again.")

    assert ner_ctor.call_count == 1
    assert rel_ctor.call_count == 1


def test_semantic_network_extractor_reuses_sub_extractors():
    ner_instance = MagicMock()
    ner_instance.extract_entities.return_value = [
        Entity(text="A", label="PERSON", start_char=0, end_char=1, confidence=1.0)
    ]

    rel_instance = MagicMock()
    rel_instance.extract_relations.return_value = []

    ner_ctor = MagicMock(return_value=ner_instance)
    rel_ctor = MagicMock(return_value=rel_instance)

    with patch("veritasreason.semantic_extract.ner_extractor.NERExtractor", ner_ctor), patch(
        "veritasreason.semantic_extract.relation_extractor.RelationExtractor", rel_ctor
    ):
        extractor = SemanticNetworkExtractor(method="pattern")
        extractor.extract_network("A text.")
        extractor.extract_network("A text again.")

    assert ner_ctor.call_count == 1
    assert rel_ctor.call_count == 1
