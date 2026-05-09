import pytest

from veritasreason.normalize.text_cleaner import TextCleaner
from veritasreason.normalize.text_normalizer import TextNormalizer


def test_html_removal_reg_vs_bs4(benchmark, generate_text_data):
    """
    Compare regex vs BeautifulSoup.
    """
    cleaner = TextCleaner()
    html_content = generate_text_data("html", 10_000)

    def run():
        return cleaner.remove_html(html_content, preserve_structure=False)

    benchmark.pedantic(run, rounds=50, iterations=10)


def test_unicode_normalization_throughput(benchmark, generate_text_data):
    """
    Benchmarks unicode NFC normalization speed.
    """
    normalizer = TextNormalizer()
    text = generate_text_data("unicode", 50_000)

    def run():
        return normalizer.normalize_text(text, unicode_form="NFC")

    benchmark.pedantic(run, iterations=5, rounds=10)


def test_whitespace_normalization(benchmark, generate_text_data):
    """Benchmarks whitespace regex replacement."""
    normalizer = TextNormalizer()
    text = generate_text_data("dirty", 50_000)

    benchmark.pedantic(
        lambda: normalizer.normalize_text(text, unicode_form="NFC"),
        iterations=5,
        rounds=10,
    )
