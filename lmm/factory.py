
import os
from .ollama_provider import OllamaProvider
from .gemini_provide import GoogleProvider
from .mlx_provider import MLXProvider


def get_lmm_provider(provider: str = None):
    # An explicit argument wins over the env default so callers can switch
    # providers per request; falls back to LLM_PROVIDER, then to ollama.
    llm_provider = provider or os.getenv("LLM_PROVIDER", "ollama")

    if llm_provider == "ollama":
        model_url = os.getenv("MODEL_URL", "http://localhost:11434")
        return OllamaProvider(host=model_url)

    if llm_provider == "google":
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise Exception("GOOGLE_API_KEY is not set in the environment variables.")
        return GoogleProvider(api_key=google_api_key)

    if llm_provider == "mlx":
        # Points at a local `mlx_lm.server` (OpenAI-compatible). Note the /v1
        # suffix the OpenAI client expects on the base URL.
        base_url = os.getenv("MLX_BASE_URL", "http://localhost:8080/v1")
        return MLXProvider(base_url=base_url)

    raise Exception(f"Unknown provider: {llm_provider}")


def get_available_models(provider: str = None):
    return get_lmm_provider(provider).list_models()


def is_model_installed(model_name: str, provider: str = None) -> bool:
    return get_lmm_provider(provider).is_model_installed(model_name)
