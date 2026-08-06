from abc import ABC, abstractmethod

class LMMProvider(ABC):
    @abstractmethod
    def chat(self ,model, messages, stream= False, tools = None, options=None, thinking= False):
        pass