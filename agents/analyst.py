from typing import Generator
import anthropic
from config import MODELS, MAX_TOKENS


class AnalystAgent:
    """
    Analyst uses Opus with adaptive thinking for deep technical analysis.
    Streaming is mandatory here — thinking + long output would timeout otherwise.
    """

    role = "analyst"
    _system = [
        {
            "type": "text",
            "text": (
                "You are a senior technical analyst and solutions architect. You specialize in:\n"
                "- Requirements analysis and PRD writing\n"
                "- System design and architecture decisions\n"
                "- Technical feasibility assessment\n"
                "- Risk analysis and mitigation strategies\n"
                "- API contracts and data modeling\n"
                "- Technology stack evaluation and trade-off analysis\n\n"
                "Think deeply before responding. Structure your analysis clearly with sections. "
                "Consider long-term maintainability, scalability, and team capabilities. "
                "Be decisive — provide clear recommendations, not just options."
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.model = MODELS["analyst"]
        self.max_tokens = MAX_TOKENS["analyst"]

    def stream(self, messages: list[dict]) -> Generator[str, None, None]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=self._system,
            messages=messages,
        ) as s:
            for event in s:
                if (
                    hasattr(event, "type")
                    and event.type == "content_block_delta"
                    and hasattr(event.delta, "type")
                    and event.delta.type == "text_delta"
                ):
                    yield event.delta.text

    def respond(self, messages: list[dict]) -> str:
        return "".join(self.stream(messages))
