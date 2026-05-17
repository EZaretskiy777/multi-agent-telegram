import anthropic
from config import MODELS, MAX_TOKENS
from .base import AGENT_TOOLS, execute_tool


class AnalystAgent:
    role = "analyst"
    system_prompt = (
        "You are a senior technical analyst and solutions architect. You specialize in:\n"
        "- Requirements analysis and PRD writing\n"
        "- System design and architecture decisions\n"
        "- Technical feasibility assessment\n"
        "- Risk analysis and mitigation strategies\n"
        "- API contracts and data modeling\n"
        "- Technology stack evaluation and trade-off analysis\n\n"
        "Think deeply before responding. Structure your analysis clearly with sections. "
        "Consider long-term maintainability, scalability, and team capabilities. "
        "Be decisive — provide clear recommendations, not just options.\n\n"
        "You have tools to manage projects, create Linear issues, Notion pages, and read GitHub repos. "
        "Always respond in the same language the user writes in."
    )

    def __init__(self, client: anthropic.AsyncAnthropic):
        self.client = client
        self.model = MODELS["analyst"]
        self.max_tokens = MAX_TOKENS["analyst"]
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
                thinking={"type": "adaptive"},
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
