import pytest

from veritasreason.normalize.date_normalizer import DateNormalizer
from veritasreason.normalize.number_normalizer import NumberNormalizer


@pytest.mark.parametrize("date_str", ["2026-02-03", "Ferbuary 2nd, 2026", "9 days ago"])
def test_data_parsing_variations(benchmark, date_str):
    """Compare speed of different date formats."""
    normalizer = DateNormalizer()
    benchmark.pedantic(
        lambda: normalizer.normalize_date(date_str), iterations=10, rounds=20
    )


def test_number_normalization(benchmark):
    """Benchmarks number parsing with currency and unit stripping."""
    normalizer = NumberNormalizer()
    raw_inputs = ["$1,234.56", "1.5k", "50%", "1,000,000"] * 100

    def run():
        for n in raw_inputs:
            normalizer.normalize_number(n)

    benchmark.pedantic(run, iterations=5, rounds=20)
