"""Shared helper for the chat stream."""

import json


def ndjson(*, content=None, thinking=None, done=False) -> str:
    """One NDJSON stream line in the wire shape the client expects."""
    return json.dumps(
        {"content": content, "thinking": thinking, "done": done}) + "\n"
