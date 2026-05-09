"""
Provenance-enabled wrappers for LLM providers.

This module provides provenance tracking for all LLM operations:
- Groq LLM
- OpenAI LLM
- HuggingFace LLM
- LiteLLM

Tracks: model name, tokens (prompt/completion), cost, latency, prompts, responses

All classes wrap the original LLM providers and add optional provenance tracking
without modifying existing functionality.

Usage:
    from veritasreason.llms.llms_provenance import (
        GroqLLMWithProvenance,
        OpenAILLMWithProvenance
    )
    
    # Enable provenance tracking
    llm = GroqLLMWithProvenance(provenance=True)
    response = llm.generate("What is artificial intelligence?")
    
    # Provenance automatically tracks:
    # - Model used
    # - Token counts
    # - API costs
    # - Latency
    # - Prompt and response previews

Features:
    - Zero breaking changes - works exactly like original LLM classes
    - Opt-in provenance via provenance=True parameter
    - Tracks all API calls with complete metadata
    - Cost tracking for budget monitoring
    - Performance monitoring (latency)
    - Graceful degradation if provenance module unavailable

Author: VeritasReason Contributors
License: MIT
"""

from typing import Optional, Dict, Any
import time
import uuid


class LLMProvenanceMixin:
    """
    Mixin to add provenance tracking to any LLM provider.
    
    This mixin provides common provenance infrastructure for tracking
    LLM API calls including tokens, costs, and performance metrics.
    """
    
    def __init__(self, provenance: bool = False, **kwargs):
        """
        Initialize LLM provenance tracking.
        
        Args:
            provenance: Enable provenance tracking (default: False)
            **kwargs: Additional arguments passed to parent class
        """
        self.provenance = provenance
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                # Graceful degradation if provenance module not available
                self.provenance = False
    
    def _track_llm_call(
        self,
        call_id: str,
        prompt: str,
        response: Any,
        **metadata
    ) -> None:
        """
        Track LLM API call with provenance.
        
        Args:
            call_id: Unique identifier for this API call
            prompt: Input prompt
            response: LLM response
            **metadata: Additional metadata (tokens, cost, latency, etc.)
        """
        if self.provenance and self._prov_manager:
            # Extract response text
            response_text = response
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif not isinstance(response, str):
                response_text = str(response)
            
            self._prov_manager.track_entity(
                entity_id=call_id,
                source=f"{self.__class__.__name__}_api",
                entity_type="llm_generation",
                metadata={
                    "model": getattr(self, 'model', 'unknown'),
                    "prompt_preview": prompt[:200] if len(prompt) > 200 else prompt,
                    "response_preview": response_text[:200] if len(str(response_text)) > 200 else str(response_text),
                    **metadata
                }
            )


class GroqLLMWithProvenance(LLMProvenanceMixin):
    """
    Groq LLM with provenance tracking.
    
    Wraps the original GroqLLM and tracks all API calls with complete metadata.
    
    Example:
        >>> llm = GroqLLMWithProvenance(provenance=True, model="llama-3.1-70b")
        >>> response = llm.generate("Explain quantum computing")
        >>> # API call is tracked with model, tokens, cost, latency
    """
    
    def __init__(self, provenance: bool = False, **config):
        """
        Initialize Groq LLM with optional provenance.
        
        Args:
            provenance: Enable provenance tracking (default: False)
            **config: Configuration passed to original GroqLLM
        """
        from .groq_llm import GroqLLM
        
        LLMProvenanceMixin.__init__(self, provenance=provenance)
        self._llm = GroqLLM(**config)
        self.model = getattr(self._llm, 'model', 'groq')
    
    def generate(self, prompt: str, **kwargs):
        """
        Generate response with provenance tracking.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            LLM response (same format as original GroqLLM)
        """
        start_time = time.time()
        response = self._llm.generate(prompt, **kwargs)
        elapsed = time.time() - start_time
        
        if self.provenance:
            # Extract token counts if available
            prompt_tokens = None
            completion_tokens = None
            total_cost = None
            
            if hasattr(response, 'usage'):
                prompt_tokens = getattr(response.usage, 'prompt_tokens', None)
                completion_tokens = getattr(response.usage, 'completion_tokens', None)
            
            if hasattr(response, 'cost'):
                total_cost = response.cost
            
            self._track_llm_call(
                call_id=f"groq_call_{uuid.uuid4().hex[:8]}",
                prompt=prompt,
                response=response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=(prompt_tokens + completion_tokens) if (prompt_tokens and completion_tokens) else None,
                total_cost=total_cost,
                latency_seconds=elapsed,
                temperature=kwargs.get('temperature'),
                max_tokens=kwargs.get('max_tokens'),
                top_p=kwargs.get('top_p')
            )
        
        return response
    
    def __getattr__(self, name):
        """Delegate other methods to wrapped LLM."""
        return getattr(self._llm, name)


class OpenAILLMWithProvenance(LLMProvenanceMixin):
    """
    OpenAI LLM with provenance tracking.
    
    Wraps the original OpenAILLM and tracks all API calls.
    """
    
    def __init__(self, provenance: bool = False, **config):
        """
        Initialize OpenAI LLM with optional provenance.
        
        Args:
            provenance: Enable provenance tracking (default: False)
            **config: Configuration passed to original OpenAILLM
        """
        from .openai_llm import OpenAILLM
        
        LLMProvenanceMixin.__init__(self, provenance=provenance)
        self._llm = OpenAILLM(**config)
        self.model = getattr(self._llm, 'model', 'openai')
    
    def generate(self, prompt: str, **kwargs):
        """
        Generate response with provenance tracking.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            LLM response
        """
        start_time = time.time()
        response = self._llm.generate(prompt, **kwargs)
        elapsed = time.time() - start_time
        
        if self.provenance:
            # Extract token counts if available
            prompt_tokens = None
            completion_tokens = None
            total_cost = None
            
            if hasattr(response, 'usage'):
                prompt_tokens = getattr(response.usage, 'prompt_tokens', None)
                completion_tokens = getattr(response.usage, 'completion_tokens', None)
            
            if hasattr(response, 'cost'):
                total_cost = response.cost
            
            self._track_llm_call(
                call_id=f"openai_call_{uuid.uuid4().hex[:8]}",
                prompt=prompt,
                response=response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=(prompt_tokens + completion_tokens) if (prompt_tokens and completion_tokens) else None,
                total_cost=total_cost,
                latency_seconds=elapsed,
                temperature=kwargs.get('temperature'),
                max_tokens=kwargs.get('max_tokens')
            )
        
        return response
    
    def __getattr__(self, name):
        """Delegate other methods to wrapped LLM."""
        return getattr(self._llm, name)


class HuggingFaceLLMWithProvenance(LLMProvenanceMixin):
    """
    HuggingFace LLM with provenance tracking.
    
    Wraps the original HuggingFaceLLM and tracks all generations.
    """
    
    def __init__(self, provenance: bool = False, **config):
        """
        Initialize HuggingFace LLM with optional provenance.
        
        Args:
            provenance: Enable provenance tracking (default: False)
            **config: Configuration passed to original HuggingFaceLLM
        """
        from .huggingface_llm import HuggingFaceLLM
        
        LLMProvenanceMixin.__init__(self, provenance=provenance)
        self._llm = HuggingFaceLLM(**config)
        self.model = getattr(self._llm, 'model', 'huggingface')
    
    def generate(self, prompt: str, **kwargs):
        """
        Generate response with provenance tracking.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            LLM response
        """
        start_time = time.time()
        response = self._llm.generate(prompt, **kwargs)
        elapsed = time.time() - start_time
        
        if self.provenance:
            self._track_llm_call(
                call_id=f"hf_call_{uuid.uuid4().hex[:8]}",
                prompt=prompt,
                response=response,
                latency_seconds=elapsed,
                max_length=kwargs.get('max_length'),
                temperature=kwargs.get('temperature')
            )
        
        return response
    
    def __getattr__(self, name):
        """Delegate other methods to wrapped LLM."""
        return getattr(self._llm, name)


class LiteLLMWithProvenance(LLMProvenanceMixin):
    """
    LiteLLM with provenance tracking.
    
    Wraps the original LiteLLM and tracks all API calls across providers.
    """
    
    def __init__(self, provenance: bool = False, **config):
        """
        Initialize LiteLLM with optional provenance.
        
        Args:
            provenance: Enable provenance tracking (default: False)
            **config: Configuration passed to original LiteLLM
        """
        from .lite_llm import LiteLLM
        
        LLMProvenanceMixin.__init__(self, provenance=provenance)
        self._llm = LiteLLM(**config)
        self.model = getattr(self._llm, 'model', 'litellm')
    
    def generate(self, prompt: str, **kwargs):
        """
        Generate response with provenance tracking.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            LLM response
        """
        start_time = time.time()
        response = self._llm.generate(prompt, **kwargs)
        elapsed = time.time() - start_time
        
        if self.provenance:
            # LiteLLM provides unified response format
            prompt_tokens = None
            completion_tokens = None
            total_cost = None
            
            if hasattr(response, 'usage'):
                prompt_tokens = getattr(response.usage, 'prompt_tokens', None)
                completion_tokens = getattr(response.usage, 'completion_tokens', None)
            
            if hasattr(response, '_hidden_params') and 'response_cost' in response._hidden_params:
                total_cost = response._hidden_params['response_cost']
            
            self._track_llm_call(
                call_id=f"lite_call_{uuid.uuid4().hex[:8]}",
                prompt=prompt,
                response=response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_cost=total_cost,
                latency_seconds=elapsed,
                provider=kwargs.get('provider')
            )
        
        return response
    
    def __getattr__(self, name):
        """Delegate other methods to wrapped LLM."""
        return getattr(self._llm, name)


# Convenience exports
__all__ = [
    'GroqLLMWithProvenance',
    'OpenAILLMWithProvenance',
    'HuggingFaceLLMWithProvenance',
    'LiteLLMWithProvenance',
    'LLMProvenanceMixin',
]
