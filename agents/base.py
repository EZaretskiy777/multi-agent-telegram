import anthropic
from typing import Generator
from config import MODELS, MAX_TOKENS


class BaseAgent:
    """
    Base agent with prompt caching built-in.

    System prompts are cached after the first call — subsequent requests
    to the same agent cost ~90% less for the cached prefix.
    """

    role: str = ""
    system_prompt: str = ""

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.model = MODELS[self.role]
        self.max_tokens = MAX_TOKENS[self.role]
        # cache_control on the system prompt: once warmed, costs ~0.1x per request
        self._system = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def respond(self, messages: list[dict]) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._system,
            messages=messages,
        )
        return response.content[0].text

    def stream(self, messages: list[dict]) -> Generator[str, None, None]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._system,
            messages=messages,
        ) as s:
            yield from s.text_stream
