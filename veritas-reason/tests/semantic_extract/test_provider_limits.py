
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure we test the local code, not the installed package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from veritasreason.semantic_extract.ner_extractor import Entity
from veritasreason.semantic_extract.relation_extractor import Relation
from veritasreason.semantic_extract.triplet_extractor import Triplet
from veritasreason.semantic_extract.methods import extract_entities_llm
# We import providers later inside tests to allow patching

class TestSemanticClasses:
    """Test that core semantic classes do not have hardcoded max lengths."""

    def test_entity_no_max_length(self):
        long_text = "a" * 10000
        entity = Entity(text=long_text, label="TEST", start_char=0, end_char=10000)
        assert entity.text == long_text
        assert len(entity.text) == 10000

    def test_relation_no_max_length(self):
        long_text = "a" * 10000
        e1 = Entity(text="s", label="S", start_char=0, end_char=1)
        e2 = Entity(text="o", label="O", start_char=0, end_char=1)
        relation = Relation(subject=e1, predicate=long_text, object=e2)
        assert relation.predicate == long_text

    def test_triplet_no_max_length(self):
        long_text = "a" * 10000
        triplet = Triplet(subject=long_text, predicate="r", object="t")
        assert triplet.subject == long_text


class TestProviderLimits:
    """Test that providers pass through correct length parameters."""

    def test_openai_max_completion_tokens(self):
        from veritasreason.semantic_extract.providers import OpenAIProvider
        
        # Patch _init_client to avoid real client creation and import issues
        with patch.object(OpenAIProvider, '_init_client', return_value=None):
            provider = OpenAIProvider(api_key="fake")
            
            # Manually mock client
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client
            
            provider.generate("prompt", max_completion_tokens=12345, top_p=0.9)

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["max_completion_tokens"] == 12345
            assert call_kwargs["top_p"] == 0.9
            assert "max_tokens" not in call_kwargs

    def test_anthropic_max_tokens_defaults(self):
        from veritasreason.semantic_extract.providers import AnthropicProvider
        
        with patch.object(AnthropicProvider, '_init_client', return_value=None):
            provider = AnthropicProvider(api_key="fake")
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="result")]
            mock_client.messages.create.return_value = mock_response
            provider.client = mock_client
            
            provider.generate("prompt")
            
            # Verify default is 8192 (new limit)
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 8192

            # Test override
            provider.generate("prompt", max_tokens=9999)
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 9999

    def test_groq_max_completion_tokens(self):
        from veritasreason.semantic_extract.providers import GroqProvider
        
        with patch.object(GroqProvider, '_init_client', return_value=None):
            provider = GroqProvider(api_key="fake")
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client
            
            provider.generate("prompt", max_completion_tokens=5000)

            # Verify
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["max_completion_tokens"] == 5000

    def test_gemini_params(self):
        from veritasreason.semantic_extract.providers import GeminiProvider
        
        with patch.object(GeminiProvider, '_init_client', return_value=None):
            provider = GeminiProvider(api_key="fake")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "result"
            mock_model.generate_content.return_value = mock_response
            provider.client = mock_model
            
            provider.generate("prompt", top_k=10, candidate_count=2)

            # Verify
            call_kwargs = mock_model.generate_content.call_args[1]
            gen_config = call_kwargs["generation_config"]
            assert gen_config["top_k"] == 10
            assert gen_config["candidate_count"] == 2

class TestTemperatureParameter:
    """Test that temperature=None omits the parameter from API calls."""

    def test_openai_temperature_none_omitted(self):
        """Verify temperature is NOT in kwargs when None."""
        from veritasreason.semantic_extract.providers import OpenAIProvider

        with patch.object(OpenAIProvider, '_init_client', return_value=None):
            provider = OpenAIProvider(api_key="fake")
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt")  # No temperature

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "temperature" not in call_kwargs

    def test_openai_temperature_explicit_included(self):
        """Verify temperature IS in kwargs when explicitly set."""
        from veritasreason.semantic_extract.providers import OpenAIProvider

        with patch.object(OpenAIProvider, '_init_client', return_value=None):
            provider = OpenAIProvider(api_key="fake")
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt", temperature=0.5)

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["temperature"] == 0.5

    def test_groq_temperature_none_omitted(self):
        """Verify temperature is NOT in kwargs when None for Groq."""
        from veritasreason.semantic_extract.providers import GroqProvider

        with patch.object(GroqProvider, '_init_client', return_value=None):
            provider = GroqProvider(api_key="fake")
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt")  # No temperature

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "temperature" not in call_kwargs

    def test_groq_temperature_explicit_included(self):
        """Verify temperature IS in kwargs when explicitly set for Groq."""
        from veritasreason.semantic_extract.providers import GroqProvider

        with patch.object(GroqProvider, '_init_client', return_value=None):
            provider = GroqProvider(api_key="fake")
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt", temperature=0.7)

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["temperature"] == 0.7

    def test_gemini_temperature_none_omitted(self):
        """Verify generation_config is None or empty when temperature not set for Gemini."""
        from veritasreason.semantic_extract.providers import GeminiProvider

        with patch.object(GeminiProvider, '_init_client', return_value=None):
            provider = GeminiProvider(api_key="fake")
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "result"
            mock_model.generate_content.return_value = mock_response
            provider.client = mock_model

            provider.generate("prompt")  # No temperature

            call_kwargs = mock_model.generate_content.call_args[1]
            gen_config = call_kwargs.get("generation_config")
            # When no config params set, config is None or empty dict
            assert gen_config is None or "temperature" not in gen_config

    def test_gemini_temperature_explicit_included(self):
        """Verify temperature IS in generation_config when explicitly set for Gemini."""
        from veritasreason.semantic_extract.providers import GeminiProvider

        with patch.object(GeminiProvider, '_init_client', return_value=None):
            provider = GeminiProvider(api_key="fake")
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "result"
            mock_model.generate_content.return_value = mock_response
            provider.client = mock_model

            provider.generate("prompt", temperature=0.8)

            call_kwargs = mock_model.generate_content.call_args[1]
            gen_config = call_kwargs["generation_config"]
            assert gen_config["temperature"] == 0.8

    def test_ollama_temperature_none_omitted(self):
        """Verify options is None or has no temperature when None for Ollama."""
        from veritasreason.semantic_extract.providers import OllamaProvider

        with patch.object(OllamaProvider, '_init_client', return_value=None):
            provider = OllamaProvider()
            mock_client = MagicMock()
            mock_response = {"response": "result"}
            mock_client.generate.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt")  # No temperature

            call_kwargs = mock_client.generate.call_args[1]
            options = call_kwargs.get("options")
            # When no options params set, options is None or empty dict
            assert options is None or "temperature" not in options

    def test_ollama_temperature_explicit_included(self):
        """Verify temperature IS in options when explicitly set for Ollama."""
        from veritasreason.semantic_extract.providers import OllamaProvider

        with patch.object(OllamaProvider, '_init_client', return_value=None):
            provider = OllamaProvider()
            mock_client = MagicMock()
            mock_response = {"response": "result"}
            mock_client.generate.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt", temperature=0.3)

            call_kwargs = mock_client.generate.call_args[1]
            options = call_kwargs.get("options", {})
            assert options["temperature"] == 0.3

    def test_ollama_default_base_url_used_as_host(self):
        """Client must be instantiated with host=base_url (default localhost)."""
        from veritasreason.semantic_extract.providers import OllamaProvider

        mock_ollama = MagicMock()
        mock_client_instance = MagicMock()
        mock_ollama.Client.return_value = mock_client_instance

        with patch.dict('sys.modules', {'ollama': mock_ollama}):
            # Reload so _init_client picks up the patched module
            provider = OllamaProvider.__new__(OllamaProvider)
            provider.base_url = "http://localhost:11434"
            provider.model = "llama2"
            provider.logger = MagicMock()
            provider.client = None
            provider._init_client()

        mock_ollama.Client.assert_called_once_with(host="http://localhost:11434")
        assert provider.client is mock_client_instance

    def test_ollama_custom_base_url_passed_as_host(self):
        """Client must be instantiated with host set to the custom base_url."""
        from veritasreason.semantic_extract.providers import OllamaProvider

        mock_ollama = MagicMock()
        mock_client_instance = MagicMock()
        mock_ollama.Client.return_value = mock_client_instance

        with patch.dict('sys.modules', {'ollama': mock_ollama}):
            provider = OllamaProvider.__new__(OllamaProvider)
            provider.base_url = "http://192.168.1.3:11434"
            provider.model = "qwen3.5:9b"
            provider.logger = MagicMock()
            provider.client = None
            provider._init_client()

        mock_ollama.Client.assert_called_once_with(host="http://192.168.1.3:11434")
        assert provider.client is mock_client_instance

    def test_ollama_module_not_assigned_as_client(self):
        """Regression: self.client must not be the ollama module itself."""
        from veritasreason.semantic_extract.providers import OllamaProvider

        mock_ollama = MagicMock()
        mock_client_instance = MagicMock()
        mock_ollama.Client.return_value = mock_client_instance

        with patch.dict('sys.modules', {'ollama': mock_ollama}):
            provider = OllamaProvider.__new__(OllamaProvider)
            provider.base_url = "http://localhost:11434"
            provider.model = "llama2"
            provider.logger = MagicMock()
            provider.client = None
            provider._init_client()

        assert provider.client is not mock_ollama, (
            "self.client was set to the ollama module instead of ollama.Client(...)"
        )

    def test_deepseek_temperature_none_omitted(self):
        """Verify temperature is NOT in kwargs when None for DeepSeek."""
        from veritasreason.semantic_extract.providers import DeepSeekProvider

        with patch.object(DeepSeekProvider, '_init_client', return_value=None):
            provider = DeepSeekProvider(api_key="fake")
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt")  # No temperature

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "temperature" not in call_kwargs

    def test_deepseek_temperature_explicit_included(self):
        """Verify temperature IS in kwargs when explicitly set for DeepSeek."""
        from veritasreason.semantic_extract.providers import DeepSeekProvider

        with patch.object(DeepSeekProvider, '_init_client', return_value=None):
            provider = DeepSeekProvider(api_key="fake")
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "result"
            mock_client.chat.completions.create.return_value = mock_response
            provider.client = mock_client

            provider.generate("prompt", temperature=0.9)

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["temperature"] == 0.9


class TestChunkingDefaults:
    """Test that chunking defaults have been increased."""

    @patch("veritasreason.semantic_extract.methods.create_provider")
    @patch("veritasreason.semantic_extract.methods._extract_entities_chunked")
    def test_openai_chunking_limit(self, mock_chunked, mock_create_provider):
        # Setup
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_create_provider.return_value = mock_llm
        
        # Text length = 10000 (Greater than old 4000, less than new 64000)
        long_text = "a" * 10000
        
        # Call without explicit max_text_length
        extract_entities_llm(long_text, provider="openai", api_key="fake")
        
        # Should NOT call chunked extraction because default is now 64000
        mock_chunked.assert_not_called()

    @patch("veritasreason.semantic_extract.methods.create_provider")
    @patch("veritasreason.semantic_extract.methods._extract_entities_chunked")
    def test_groq_chunking_limit(self, mock_chunked, mock_create_provider):
        # Setup
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_create_provider.return_value = mock_llm
        
        # Text length = 10000 (Greater than old 8000, less than new 64000)
        long_text = "a" * 10000
        
        extract_entities_llm(long_text, provider="groq", api_key="fake")
        
        # Should NOT call chunked extraction because default is now 64000
        mock_chunked.assert_not_called()
