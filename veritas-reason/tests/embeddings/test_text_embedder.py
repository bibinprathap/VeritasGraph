import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import sys

# Import the module to be tested
from veritasreason.embeddings.text_embedder import TextEmbedder
from veritasreason.utils.exceptions import ProcessingError

class TestTextEmbedder(unittest.TestCase):
    
    def setUp(self):
        # Create a mock for sentence_transformers.SentenceTransformer
        self.mock_st_patcher = patch('veritasreason.embeddings.text_embedder.SentenceTransformer')
        self.mock_st_class = self.mock_st_patcher.start()
        
        # Create a mock for fastembed.TextEmbedding
        self.mock_fe_patcher = patch('veritasreason.embeddings.text_embedder.TextEmbedding')
        self.mock_fe_class = self.mock_fe_patcher.start()
        
        # Patch availability flags
        self.st_avail_patcher = patch('veritasreason.embeddings.text_embedder.SENTENCE_TRANSFORMERS_AVAILABLE', True)
        self.st_avail_patcher.start()
        
        self.fe_avail_patcher = patch('veritasreason.embeddings.text_embedder.FASTEMBED_AVAILABLE', True)
        self.fe_avail_patcher.start()

    def tearDown(self):
        self.mock_st_patcher.stop()
        self.mock_fe_patcher.stop()
        self.st_avail_patcher.stop()
        self.fe_avail_patcher.stop()

    def test_init_default(self):
        """Test initialization with default parameters (fastembed)."""
        embedder = TextEmbedder()
        self.assertEqual(embedder.method, "fastembed")
        self.assertEqual(embedder.model_name, "BAAI/bge-small-en-v1.5")
        self.mock_fe_class.assert_called_once()
        self.assertIsNotNone(embedder.fastembed_model)
        self.assertIsNone(embedder.model)

    def test_init_sentence_transformers(self):
        """Test initialization with sentence-transformers method."""
        embedder = TextEmbedder(method="sentence_transformers")
        self.assertEqual(embedder.method, "sentence_transformers")
        self.mock_st_class.assert_called_once()
        self.assertIsNotNone(embedder.model)
        self.assertIsNone(embedder.fastembed_model)

    def test_init_fastembed(self):
        """Test initialization with fastembed method."""
        embedder = TextEmbedder(method="fastembed")
        self.assertEqual(embedder.method, "fastembed")
        self.mock_fe_class.assert_called_once()
        self.assertIsNotNone(embedder.fastembed_model)
        self.assertIsNone(embedder.model)

    def test_embed_text_sentence_transformers(self):
        """Test embedding generation with sentence-transformers."""
        embedder = TextEmbedder(method="sentence_transformers")
        
        # Mock the encode method
        mock_embedding = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
        embedder.model.encode.return_value = mock_embedding
        
        result = embedder.embed_text("test text")
        
        self.assertTrue(np.array_equal(result, mock_embedding[0]))
        embedder.model.encode.assert_called_with(["test text"], normalize_embeddings=True)

    def test_embed_text_fastembed(self):
        """Test embedding generation with fastembed."""
        embedder = TextEmbedder(method="fastembed")
        
        # Mock the embed method
        mock_embedding = [0.1, 0.2, 0.3]
        # FastEmbed returns a generator of embeddings
        embedder.fastembed_model.embed.return_value = iter([mock_embedding])
        
        result = embedder.embed_text("test text", normalize=False)
        
        # Note: TextEmbedder.embed_text normalizes manually for FastEmbed if self.normalize is True
        # Default is True. The mock result [0.1, 0.2, 0.3] will be normalized.
        expected_norm = np.linalg.norm(np.array(mock_embedding, dtype=np.float32))
        expected = np.array(mock_embedding, dtype=np.float32) / expected_norm
        
        self.assertTrue(np.allclose(result, expected))
        embedder.fastembed_model.embed.assert_called_with(["test text"])

    def test_embed_text_empty(self):
        """Test error handling for empty text."""
        embedder = TextEmbedder()
        with self.assertRaises(ProcessingError):
            embedder.embed_text("")
        with self.assertRaises(ProcessingError):
            embedder.embed_text("   ")

    def test_embed_batch_sentence_transformers(self):
        """Test batch embedding with sentence-transformers."""
        embedder = TextEmbedder(method="sentence_transformers")
        
        # Mock the encode method
        mock_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        embedder.model.encode.return_value = mock_embeddings
        
        texts = ["text1", "text2"]
        results = embedder.embed_batch(texts)
        
        self.assertTrue(np.array_equal(results, mock_embeddings))
        embedder.model.encode.assert_called_with(texts, normalize_embeddings=True)

    def test_embed_batch_fastembed(self):
        """Test batch embedding with fastembed."""
        embedder = TextEmbedder(method="fastembed")
        
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        embedder.fastembed_model.embed.return_value = iter(mock_embeddings)
        
        texts = ["text1", "text2"]
        results = embedder.embed_batch(texts)
        
        # Should be normalized manually
        expected = np.array(mock_embeddings, dtype=np.float32)
        norms = np.linalg.norm(expected, axis=1, keepdims=True)
        expected = expected / norms
        
        self.assertTrue(np.allclose(results, expected))

    def test_fallback_method(self):
        """Test fallback method when libraries are unavailable."""
        # Unpatch availability to simulate missing libraries
        self.st_avail_patcher.stop()
        self.fe_avail_patcher.stop()
        
        with patch('veritasreason.embeddings.text_embedder.SENTENCE_TRANSFORMERS_AVAILABLE', False), \
             patch('veritasreason.embeddings.text_embedder.FASTEMBED_AVAILABLE', False):
            
            embedder = TextEmbedder()
            self.assertIsNone(embedder.model)
            self.assertIsNone(embedder.fastembed_model)
            
            # Should use fallback (hashing)
            result = embedder.embed_text("test")
            self.assertIsInstance(result, np.ndarray)
            # Check length is 128 (as per fallback implementation)
            self.assertTrue(len(result) <= 128) 
            
            # Batch fallback
            results = embedder.embed_batch(["t1", "t2"])
            self.assertEqual(len(results), 2)

    def test_set_model(self):
        """Test dynamic model switching."""
        embedder = TextEmbedder() # Default FastEmbed
        self.assertEqual(embedder.method, "fastembed")
        
        embedder.set_model(method="sentence_transformers", model_name="new-model")
        self.assertEqual(embedder.method, "sentence_transformers")
        self.assertEqual(embedder.model_name, "new-model")
        self.mock_st_class.assert_called()

if __name__ == '__main__':
    unittest.main()
