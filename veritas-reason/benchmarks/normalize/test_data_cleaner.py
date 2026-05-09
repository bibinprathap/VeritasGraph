import pytest

from veritasreason.normalize.data_cleaner import DataCleaner


@pytest.mark.parametrize("rows", [100, 500])
def test_duplication_detection_scaling(benchmark, generate_dataset, rows):
    """
    Benchmarks duplicate detection scaling.
    """

    cleaner = DataCleaner()
    dataset = generate_dataset(rows=rows, duplicate_rate=0.2)

    def run():
        return cleaner.detect_duplicates(dataset, key_fields=["name", "email"])

    benchmark.pedantic(run, iterations=1, rounds=5)


def test_missing_value_imputation(benchmark, generate_dataset):
    """
    Benchmarks statistical imputation.
    """
    cleaner = DataCleaner()

    def setup_broken_dataset():
        dataset = generate_dataset(rows=5000)
        for row in dataset:
            if row["id"] % 5 == 0:
                row["value"] = None

        return (dataset,), {}

    def run(data):
        return cleaner.handle_missing_values(data, strategy="impute", method="mean")

    benchmark.pedantic(target=run, setup=setup_broken_dataset, iterations=1, rounds=10)
