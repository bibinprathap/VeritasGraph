import pytest

from veritasreason.ingest.file_ingestor import FileIngestor


def test_ingest_file_performance(benchmark, sample_text_file):
    """
    Benchmarks the speed of the ingest_file method

    Metrics:
    - Time to open, read, validate and wrap a ~~10 KB text file.
    """

    ingestor = FileIngestor()
    result = benchmark(
        ingestor.ingest_file, file_path=sample_text_file, read_content=True
    )

    assert result is not None
    assert result.size > 0
    assert result.name.endswith(".txt")
    assert "Line 0" in result.text
