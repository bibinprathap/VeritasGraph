import numpy as np
import pytest

from veritasreason.export.vector_exporter import VectorExporter


@pytest.mark.benchmark(group="vector_io")
@pytest.mark.parametrize("count", [1000, 10000])
def test_numpy_compression_speed(benchmark, tmp_path, generate_vectors, count):
    """
    Measures cost of np.savez_compressed.
    """
    vectors = generate_vectors(count)
    exporter = VectorExporter(format="numpy")
    output_file = tmp_path / "vectors.npz"

    def run():
        exporter.export(vectors, output_file)

    benchmark(run)


@pytest.mark.benchmark(group="vector_io")
def test_json_vector_overhead(benchmark, tmp_path, generate_vectors):
    """
    Benchmarks JSON export for vectors.
    """

    vectors = generate_vectors(2000)
    exporter = VectorExporter(format="json")
    output_file = tmp_path / "vectors.json"

    def run():
        exporter.export(vectors, output_file)

    benchmark(run)


@pytest.mark.benchmark(group="vector_io")
def test_binary_raw_throughput(benchmark, tmp_path, generate_vectors):
    """
    Measures raw binary dump speed (no compression, no metadata).
    """
    vectors = generate_vectors(10000)
    exporter = VectorExporter(format="binary")
    output_file = tmp_path / "vectors.bin"

    def run():
        exporter.export(vectors, output_file)

    benchmark(run)
