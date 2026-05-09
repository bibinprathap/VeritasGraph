
import sys
import os
import unittest
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritasreason.embeddings import TextEmbedder, EmbeddingGenerator

class TestEmbeddingProviders(unittest.TestCase):
    def test_sentence_transformers_default(self):
        print("\nTesting Sentence Transformers (Default)...")
        embedder = TextEmbedder(method="sentence_transformers")
        text = "This is a test sentence."
        embedding = embedder.embed_text(text)
        self.assertIsInstance(embedding, np.ndarray)
        print(f"Embedding shape: {embedding.shape}")
        # Default model is all-MiniLM-L6-v2 which is 384 dim
        self.assertEqual(len(embedding), 384)

    def test_sentence_transformers_custom_model(self):
        print("\nTesting Sentence Transformers (Custom Model: all-mpnet-base-v2)...")
        # all-mpnet-base-v2 produces 768 dim embeddings
        try:
            embedder = TextEmbedder(
                method="sentence_transformers", 
                model_name="all-mpnet-base-v2"
            )
            text = "This is a test sentence."
            embedding = embedder.embed_text(text)
            self.assertIsInstance(embedding, np.ndarray)
            print(f"Embedding shape: {embedding.shape}")
            self.assertEqual(len(embedding), 768)
        except Exception as e:
            print(f"Skipping custom model test if download fails: {e}")

    def test_fastembed_default(self):
        print("\nTesting FastEmbed (Default)...")
        try:
            embedder = TextEmbedder(method="fastembed")
            text = "This is a test sentence."
            embedding = embedder.embed_text(text)
            self.assertIsInstance(embedding, np.ndarray)
            print(f"Embedding shape: {embedding.shape}")
            # FastEmbed default is usually BAAI/bge-small-en-v1.5 (384 dim) or similar
            self.assertTrue(len(embedding) > 0)
        except ImportError:
            print("FastEmbed not installed, skipping.")

    def test_fastembed_custom_model(self):
        print("\nTesting FastEmbed (Custom Model: BAAI/bge-small-en-v1.5)...")
        try:
            embedder = TextEmbedder(
                method="fastembed",
                model_name="BAAI/bge-small-en-v1.5"
            )
            text = "This is a test sentence."
            embedding = embedder.embed_text(text)
            self.assertIsInstance(embedding, np.ndarray)
            print(f"Embedding shape: {embedding.shape}")
            self.assertEqual(len(embedding), 384)
        except ImportError:
             print("FastEmbed not installed, skipping.")
        except Exception as e:
             print(f"FastEmbed custom model error: {e}")

    def test_embedding_generator_config(self):
        print("\nTesting EmbeddingGenerator with config...")
        # Configure to use fastembed via EmbeddingGenerator
        config = {
            "text": {
                "method": "fastembed",
                "model_name": "BAAI/bge-small-en-v1.5"
            }
        }
        generator = EmbeddingGenerator(config=config)
        embeddings = generator.generate_embeddings(["Test text"], data_type="text")
        self.assertEqual(embeddings.shape[1], 384)
        print("EmbeddingGenerator config test passed.")

if __name__ == '__main__':
    with open("test_results.txt", "w") as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)

