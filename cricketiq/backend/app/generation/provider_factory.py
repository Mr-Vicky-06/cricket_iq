"""Factory for instantiating the active LLMProvider."""

import os
from cricketiq.backend.app.generation.contracts import LLMProvider
from cricketiq.backend.app.generation.provider import FakeLLMProvider, GeminiLLMProvider


def get_llm_provider() -> LLMProvider:
    """Return the configured LLMProvider based on CRICKETIQ_LLM_PROVIDER environment variable."""
    provider_name = os.getenv("CRICKETIQ_LLM_PROVIDER", "fake").lower()

    if provider_name in ["gemini", "google"]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            # Fallback gracefully to FakeLLMProvider if key missing in dev/test
            return FakeLLMProvider()
        return GeminiLLMProvider(api_key=api_key)

    return FakeLLMProvider()
