import anthropic
from config import MODELS, MAX_TOKENS
from .base import AGENT_TOOLS, execute_tool


class OrchestratorAgent:
    """
    General-purpose coordinator. Responds when no specific agent is mentioned.
    Also drives daily standups by querying Linear.
    Uses Haiku — cheapest model, routes and summarizes only.
    """

    role = "orchestrator"
    system_prompt = (
        "You are the team coordinator for a development team. "
        "Your job:\n"
        "1. Answer general questions about the team and project\n"
        "2. Help users understand which specialist to ask "
        "(@BackendBot, @FrontendBot, @QABot, @AnalystBot)\n"
        "3. Run daily standups by checking Linear for active tasks\n"
        "4. Keep responses concise — you are the router, not the implementer\n\n"
        "Always respond in the same language the user writes in."
    )

    def __init__(self, client: anthropic.AsyncAnthropic):
        self.client = client
        self.model = MODELS["orchestrator"]
        self.max_tokens = MAX_TOKENS["orchestrator"]
        self._system = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    @staticmethod
    def _extract_text(content: list) -> str:
        for block in content:
            if hasattr(block, "type") and block.type == "text":
                return block.text
        return ""

    async def respond(self, messages: list[dict]) -> str:
        current = list(messages)

        while True:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system,
                tools=AGENT_TOOLS,
                messages=current,
            )

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                current = current + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user",      "content": tool_results},
                ]
            else:
                return self._extract_text(response.content)
