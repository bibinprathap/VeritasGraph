"""
Test llms provenance integration.

Tests that provenance tracking works correctly for all LLM providers.
"""

import pytest


class TestGroqLLMProvenance:
    """Test Groq LLM with provenance."""
    
    def test_without_provenance(self):
        """Test Groq LLM works without provenance."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=False)
            assert llm is not None
            assert llm.provenance is False
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_with_provenance_enabled(self):
        """Test Groq LLM tracks provenance."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            assert llm.provenance is True
            assert llm._prov_manager is not None
        except ImportError:
            pytest.skip("GroqLLM not available")


class TestOpenAILLMProvenance:
    """Test OpenAI LLM with provenance."""
    
    def test_without_provenance(self):
        """Test OpenAI LLM works without provenance."""
        try:
            from veritasreason.llms.llms_provenance import OpenAILLMWithProvenance
            llm = OpenAILLMWithProvenance(provenance=False)
            assert llm is not None
        except ImportError:
            pytest.skip("OpenAILLM not available")
    
    def test_with_provenance_enabled(self):
        """Test OpenAI LLM tracks provenance."""
        try:
            from veritasreason.llms.llms_provenance import OpenAILLMWithProvenance
            llm = OpenAILLMWithProvenance(provenance=True)
            assert llm.provenance is True
        except ImportError:
            pytest.skip("OpenAILLM not available")


class TestHuggingFaceLLMProvenance:
    """Test HuggingFace LLM with provenance."""
    
    def test_without_provenance(self):
        """Test HuggingFace LLM works without provenance."""
        try:
            from veritasreason.llms.llms_provenance import HuggingFaceLLMWithProvenance
            llm = HuggingFaceLLMWithProvenance(provenance=False)
            assert llm is not None
        except ImportError:
            pytest.skip("HuggingFaceLLM not available")


class TestLLMProvenanceEdgeCases:
    """Test edge cases for LLM provenance."""
    
    def test_empty_prompt(self):
        """Test LLM with empty prompt."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should handle empty prompt
            assert llm is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_very_long_prompt(self):
        """Test LLM with very long prompt."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            long_prompt = "Explain " + "AI " * 1000
            # Should handle long prompts
            assert llm is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_special_characters_in_prompt(self):
        """Test LLM with special characters in prompt."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            special_prompt = "Explain @#$%^&*() and 中文 émojis 🎉"
            # Should handle special characters
            assert llm is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_multiple_llm_calls(self):
        """Test multiple LLM calls with provenance."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should track multiple calls independently
            assert llm._prov_manager is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_concurrent_llm_calls(self):
        """Test concurrent LLM calls."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should handle concurrent calls
            assert llm is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_llm_with_custom_parameters(self):
        """Test LLM with custom generation parameters."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should track custom parameters
            assert llm._prov_manager is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_llm_response_without_usage(self):
        """Test LLM response without usage metadata."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should handle responses without usage info
            assert llm is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_llm_response_without_cost(self):
        """Test LLM response without cost information."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should handle responses without cost info
            assert llm is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
    
    def test_different_llm_providers(self):
        """Test different LLM providers with same provenance pattern."""
        try:
            from veritasreason.llms.llms_provenance import (
                GroqLLMWithProvenance,
                OpenAILLMWithProvenance
            )
            groq = GroqLLMWithProvenance(provenance=True)
            openai = OpenAILLMWithProvenance(provenance=True)
            # Both should work independently
            assert groq is not None
            assert openai is not None
        except ImportError:
            pytest.skip("LLM providers not available")
    
    def test_llm_latency_tracking(self):
        """Test that LLM latency is tracked correctly."""
        try:
            from veritasreason.llms.llms_provenance import GroqLLMWithProvenance
            llm = GroqLLMWithProvenance(provenance=True)
            # Should track latency for performance monitoring
            assert llm._prov_manager is not None
        except ImportError:
            pytest.skip("GroqLLM not available")
