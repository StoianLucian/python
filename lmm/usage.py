from dataclasses import dataclass

# Pretend prices so we can "bill" a local model the way a paid API would.
# Real providers publish these as USD per 1,000,000 tokens.
# (These numbers are illustrative — swap in real ones if you move to a paid API.)
INPUT_PRICE_PER_1M = 3.00
OUTPUT_PRICE_PER_1M = 15.00


@dataclass
class TokenUsage:
    """Accumulates token usage across every model call in one request.

    Think of this as the running bill. Each provider response tells us how many
    tokens that specific call consumed; we add them up. On a paid API you'd be
    charged for exactly these numbers.
    """

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * INPUT_PRICE_PER_1M
            + self.output_tokens / 1_000_000 * OUTPUT_PRICE_PER_1M
        )

    def add(self, input_tokens: int, output_tokens: int) -> None:
        # `or 0` guards against None, which some responses use when a phase
        # (e.g. prompt eval) was skipped because it was cached.
        self.input_tokens += input_tokens or 0
        self.output_tokens += output_tokens or 0

    def add_ollama(self, response) -> None:
        """Read the usage counters off an Ollama response.

        Works for both the non-streaming ChatResponse object (attribute access)
        and the final streaming chunk (dict-like access on `done: true`).
        """
        if hasattr(response, "get"):
            self.add(response.get("prompt_eval_count"), response.get("eval_count"))
        else:
            self.add(
                getattr(response, "prompt_eval_count", 0),
                getattr(response, "eval_count", 0),
            )

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }
