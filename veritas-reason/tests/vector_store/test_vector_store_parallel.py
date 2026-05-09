
import unittest
import numpy as np
import time
import sys
import os
import logging
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.vector_store import VectorStore
from veritasreason.utils.exceptions import ProcessingError


class TestVectorStoreParallel(unittest.TestCase):
    def setUp(self):
        logging.getLogger("vector_store").setLevel(logging.ERROR)

        self.dimension = 4
        self.store = VectorStore(
            backend="inmemory",
            dimension=self.dimension,
        )

        self.store.embedder = MagicMock()

    def test_embed_batch_success(self):
        texts = ["a", "b", "c"]
        expected_embeddings = [
            np.array([0.1] * 4, dtype=np.float32),
            np.array([0.2] * 4, dtype=np.float32),
            np.array([0.3] * 4, dtype=np.float32),
        ]

        self.store.embedder.generate_embeddings.return_value = expected_embeddings

        results = self.store.embed_batch(texts)

        self.assertEqual(len(results), 3)
        self.assertTrue(np.allclose(results[0], expected_embeddings[0]))
        self.store.embedder.generate_embeddings.assert_called_once_with(texts)

    def test_embed_batch_fallback(self):
        texts = ["a", "b"]

        self.store.embedder.generate_embeddings.side_effect = Exception("Model error")

        results = self.store.embed_batch(texts)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].shape, (self.dimension,))
        self.assertTrue(isinstance(results[0], np.ndarray))

    def test_add_documents_empty(self):
        ids = self.store.add_documents([])
        self.assertEqual(ids, [])

    def test_add_documents_metadata_mismatch(self):
        with self.assertRaises(ValueError):
            self.store.add_documents(["doc1"], metadata=[{}, {}])

    def test_add_documents_parallel_success(self):
        num_docs = 10
        documents = [f"doc_{i}" for i in range(num_docs)]
        metadata = [{"id": i} for i in range(num_docs)]

        def mock_embed_batch(texts):
            return [np.full(self.dimension, float(i)) for i, _ in enumerate(texts)]

        with patch.object(self.store, "embed_batch", side_effect=mock_embed_batch):
            ids = self.store.add_documents(
                documents,
                metadata,
                batch_size=2,
                parallel=True,
            )

        self.assertEqual(len(ids), num_docs)
        self.assertEqual(len(self.store.vectors), num_docs)

        for i, vec_id in enumerate(ids):
            stored_meta = self.store.get_metadata(vec_id)
            self.assertEqual(stored_meta["id"], i)

    def test_add_documents_sequential_success(self):
        num_docs = 5
        documents = [f"doc_{i}" for i in range(num_docs)]

        with patch.object(self.store, "embed_batch") as mock_batch:
            mock_batch.return_value = [np.zeros(self.dimension) for _ in range(num_docs)]

            ids = self.store.add_documents(documents, parallel=False)

            self.assertEqual(len(ids), num_docs)
            self.assertEqual(mock_batch.call_count, 1)

    def test_add_documents_error_propagation(self):
        documents = ["doc1", "doc2"]

        with patch.object(self.store, "embed_batch", side_effect=ValueError("Embedding Error")):
            with self.assertRaises(Exception):
                self.store.add_documents(documents, parallel=True)

    def test_performance_simulation(self):
        num_batches = 4
        batch_delay = 0.1
        batch_size = 1
        documents = [f"doc_{i}" for i in range(num_batches)]

        def slow_embed(texts):
            time.sleep(batch_delay)
            return [np.zeros(self.dimension) for _ in texts]

        with patch.object(self.store, "embed_batch", side_effect=slow_embed):
            start_seq = time.time()
            self.store.add_documents(documents, batch_size=batch_size, parallel=False)
            dur_seq = time.time() - start_seq

            self.store.vectors = {}

            start_par = time.time()
            self.store.add_documents(documents, batch_size=batch_size, parallel=True)
            dur_par = time.time() - start_par

            print(f"\nPerformance Test:")
            print(f"Sequential Duration: {dur_seq:.4f}s")
            print(f"Parallel Duration:   {dur_par:.4f}s")
            print(f"Speedup:             {dur_seq / dur_par:.2f}x")

            self.assertLess(dur_par, dur_seq * 0.7)

    def test_add_documents_batch_size_edge_cases(self):
        documents = ["a", "b", "c"]

        with patch.object(self.store, "embed_batch") as mock_batch:
            mock_batch.side_effect = lambda texts: [np.zeros(4) for _ in texts]

            self.store.add_documents(documents, batch_size=100)
            self.assertEqual(mock_batch.call_count, 1)

            mock_batch.reset_mock()

            self.store.add_documents(documents, batch_size=1)
            self.assertEqual(mock_batch.call_count, 3)


if __name__ == "__main__":
    unittest.main()
