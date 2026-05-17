import json
import anthropic
from config import MODELS, MAX_TOKENS, AgentRole


class OrchestratorAgent:
    """
    Lightweight router using Haiku — cheapest model, single JSON response.
    Decides which specialist to invoke based on the user's request.
    """

    # Cached system prompt — Haiku, so even cheaper per token
    _system = [
        {
            "type": "text",
            "text": (
                "You are a task router for a development team. "
                "Analyze the user's request and decide which specialist should handle it.\n\n"
                "Specialists:\n"
                "- backend: server-side code, APIs, databases, Python, Go, Node.js, architecture\n"
                "- frontend: UI, HTML, CSS, React, Vue, design, user experience\n"
                "- qa: tests, QA strategy, bug reports, test automation, coverage\n"
                "- analyst: requirements, system design, technical analysis, reports, PRD\n\n"
                "Respond ONLY with valid JSON: {\"agent\": \"<role>\", \"reason\": \"<one sentence>\"}"
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    def __init__(self, client: anthropic.Anthropic):
        self.client = client

    def route(self, user_message: str) -> tuple[AgentRole, str]:
        """Returns (agent_role, reason) for the given user message."""
        response = self.client.messages.create(
            model=MODELS["orchestrator"],
            max_tokens=MAX_TOKENS["orchestrator"],
            system=self._system,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text.strip()
        try:
            data = json.loads(text)
            role = AgentRole(data["agent"])
            reason = data.get("reason", "")
        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback to analyst for ambiguous requests
            role = AgentRole.ANALYST
            reason = "Could not determine specialist, defaulting to analyst."

        return role, reason
