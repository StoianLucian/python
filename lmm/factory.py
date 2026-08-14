
import os
from .ollama_provider import OllamaProvider


def get_lmm_provider():
    llm_provider = os.getenv("LLM_PROVIDER", "ollama")
    if llm_provider == "ollama":
        model_url = os.getenv("MODEL_URL", "http://localhost:11434")
        return OllamaProvider(host=model_url)

    raise Exception("Unknown provider")
