from abc import ABC, abstractmethod

class LMMProvider(ABC):
    @abstractmethod
    def chat(self ,model, messages, stream= False, tools = None, options=None, thinking= False):
        pass

    @abstractmethod
    def list_models(self):
        """Return available chat models as [{"name": str, "id": str}, ...]."""
        pass

    @abstractmethod
    def is_model_installed(self, model_name: str) -> bool:
        """Return True if the model is available for use with this provider."""
        pass

    @abstractmethod
    def iter_stream(self, stream):
        """Normalize a provider streaming response into common events:

            {"content": str | None,
             "thinking": str | None,
             "done": bool,
             "usage": {"input": int, "output": int} | None}

        Exactly one terminal event with ``done=True`` is emitted last; ``usage``
        is populated on that event when the provider reports token counts.
        """
        pass