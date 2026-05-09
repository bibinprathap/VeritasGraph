"""Tests for RelationExtractor LLM multi-founder bug (#354)."""

import pytest
from unittest.mock import MagicMock, patch

from veritasreason.semantic_extract.methods import _parse_relation_result
from veritasreason.semantic_extract.ner_extractor import Entity


APPLE_ENTITY = Entity(text="Apple Inc.", label="ORG", start_char=0, end_char=10)
JOBS_ENTITY = Entity(text="Steve Jobs", label="PERSON", start_char=0, end_char=10)

ALL_ENTITIES = [APPLE_ENTITY, JOBS_ENTITY]

TEXT = (
    "Apple Inc. was founded by Steve Jobs, Steve Wozniak, "
    "and Ronald Wayne on April 1, 1976."
)

LLM_RESPONSE = {
    "relations": [
        {"subject": "Steve Jobs",    "predicate": "founded_by", "object": "Apple Inc.", "confidence": 0.95},
        {"subject": "Steve Wozniak", "predicate": "founded_by", "object": "Apple Inc.", "confidence": 0.93},
        {"subject": "Ronald Wayne",  "predicate": "founded_by", "object": "Apple Inc.", "confidence": 0.91},
    ]
}


def test_all_three_founders_returned():
    """Bug #354 — all co-founders from LLM response must appear as Relation objects."""
    relations = _parse_relation_result(LLM_RESPONSE, ALL_ENTITIES, TEXT, "openai", "gpt-4")

    subjects = [r.subject.text for r in relations]
    assert len(relations) == 3, f"Expected 3 relations, got {len(relations)}: {subjects}"
    assert "Steve Jobs" in subjects
    assert "Steve Wozniak" in subjects
    assert "Ronald Wayne" in subjects


def test_unmatched_entity_becomes_synthetic():
    """Entities not found by NER must appear as synthetic UNKNOWN entities, not dropped."""
    # Only Apple is in the pre-extracted list; all three founders are missing
    relations = _parse_relation_result(LLM_RESPONSE, [APPLE_ENTITY], TEXT, "openai", "gpt-4")

    assert len(relations) == 3
    for r in relations:
        if r.subject.text in ("Steve Jobs", "Steve Wozniak", "Ronald Wayne"):
            assert r.subject.label == "UNKNOWN"
            assert r.subject.metadata.get("synthetic") is True


def test_matched_entity_not_synthetic():
    """Entities that DO match pre-extracted NER results must not be marked synthetic."""
    relations = _parse_relation_result(LLM_RESPONSE, ALL_ENTITIES, TEXT, "openai", "gpt-4")

    jobs_relation = next(r for r in relations if r.subject.text == "Steve Jobs")
    assert jobs_relation.subject.label == "PERSON"
    assert not jobs_relation.subject.metadata.get("synthetic")


def test_predicate_and_confidence_preserved():
    """predicate and confidence from LLM response must be preserved."""
    relations = _parse_relation_result(LLM_RESPONSE, ALL_ENTITIES, TEXT, "openai", "gpt-4")

    for r in relations:
        assert r.predicate == "founded_by"
        assert r.confidence >= 0.9


def test_empty_llm_response_returns_empty():
    """Empty relations list from LLM must return empty list without error."""
    relations = _parse_relation_result({"relations": []}, ALL_ENTITIES, TEXT, "openai", "gpt-4")
    assert relations == []


def test_missing_subject_or_object_text_skipped():
    """Relations with empty subject or object text must be silently skipped."""
    bad_response = {
        "relations": [
            {"subject": "",             "predicate": "founded_by", "object": "Apple Inc."},
            {"subject": "Steve Jobs",   "predicate": "founded_by", "object": ""},
            {"subject": "Steve Jobs",   "predicate": "founded_by", "object": "Apple Inc."},
        ]
    }
    relations = _parse_relation_result(bad_response, ALL_ENTITIES, TEXT, "openai", "gpt-4")
    assert len(relations) == 1
