from unittest.mock import MagicMock, patch

import pytest

try:
    from veritasreason.split.sliding_window_chunker import SlidingWindowChunker
    from veritasreason.split.splitter import TextSplitter
except ImportError as e:
    pytest.skip(
        f"Skipping splitting test due to missing dependencies ({e})",
        allow_module_level=True,
    )


def test_sliding_window(benchmark, long_text_string):
    """
    Benchmarks the speed of SlidingWindowChunker in 'Fixed Size' mode
    """

    chunker = SlidingWindowChunker(chunk_size=500, overlap=50)

    if hasattr(chunker, "progress_tracker"):
        chunker.progress_tracker = MagicMock()

    result = benchmark(chunker.chunk, text=long_text_string, preserve_boundaries=False)

    assert len(result) > 0
