import anthropic
from config import MODELS, MAX_TOKENS
from .base import AGENT_TOOLS, execute_tool


class OrchestratorAgent:
    role = "orchestrator"
    system_prompt = (
        "You are the team coordinator for a development team. Your responsibilities:\n"
        "1. Create and manage projects when the user asks\n"
        "2. Switch between projects based on user requests\n"
        "3. Answer general questions and route to specialists "
        "(@BackendBot, @FrontendBot, @QABot, @AnalystBot)\n"
        "4. Run daily standups by checking Linear for active tasks\n"
        "5. Keep responses concise — you coordinate, specialists implement\n\n"
        "When the user says things like 'создай проект X', 'работаем с проектом Y', "
        "'новый проект X с репо owner/repo' — always call the appropriate project tool.\n\n"
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

    async def respond(self, messages: list[dict], chat_id: int = 0) -> str:
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
                        result = await execute_tool(block.name, block.input, chat_id)
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
