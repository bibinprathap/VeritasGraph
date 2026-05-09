from unittest.mock import MagicMock, patch

import pytest

from veritasreason.normalize.encoding_handler import EncodingHandler
from veritasreason.normalize.language_detector import LanguageDetector


def test_language_detection_throughput(benchmark, generate_text_data):
    """Benchmarks langdetect intergration."""
    detector = LanguageDetector()
    texts = [generate_text_data("clean", 200) for _ in range(50)]

    def run():
        return detector.detect_batch(texts)

    benchmark.pedantic(run, iterations=1, rounds=5)


def test_encoding_detection(benchmark):
    """Benchmarks chardet integration via EncodingHandler."""
    handler = EncodingHandler()
    data = (
        b"Wowzaaa a simple string for encoding decoding , oh encoding detection just."
        * 100
    )

    def run():
        return handler.detect(data)

    benchmark.pedantic(run, iterations=5, rounds=10)
