import anthropic
from config import MODELS, MAX_TOKENS
from integrations import linear, notion

# Tools available to all specialist agents
AGENT_TOOLS = [
    {
        "name": "create_linear_issue",
        "description": (
            "Создать задачу в Linear (доска задач команды). "
            "Используй когда пользователь просит зафиксировать задачу, баг или фичу."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string", "description": "Заголовок задачи"},
                "description": {"type": "string", "description": "Описание задачи"},
            },
            "required": ["title", "description"],
        },
    },
    {
        "name": "get_linear_issues",
        "description": "Получить список активных задач из Linear.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "create_notion_page",
        "description": (
            "Создать страницу документации в Notion. "
            "Используй когда нужно сохранить описание, спецификацию, ADR или руководство."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title":   {"type": "string", "description": "Заголовок страницы"},
                "content": {"type": "string", "description": "Содержимое страницы"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "search_notion",
        "description": "Найти страницы документации в Notion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"}
            },
            "required": ["query"],
        },
    },
]


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool call and return a string result."""
    if name == "create_linear_issue":
        result = await linear.create_issue(args["title"], args.get("description", ""))
        if "error" in result:
            return f"Ошибка Linear: {result['error']}"
        return f"Задача создана: [{result.get('identifier')}] {result.get('title')}\n{result.get('url')}"

    if name == "get_linear_issues":
        issues = await linear.get_active_issues()
        return linear.format_issues(issues)

    if name == "create_notion_page":
        result = await notion.create_page(args["title"], args["content"])
        if "error" in str(result):
            return f"Ошибка Notion: {result}"
        return f"Страница создана: {result.get('url')}"

    if name == "search_notion":
        pages = await notion.search_pages(args["query"])
        return notion.format_pages(pages)

    return f"Неизвестный инструмент: {name}"


class BaseAgent:
    role: str = ""
    system_prompt: str = ""

    def __init__(self, client: anthropic.AsyncAnthropic):
        self.client = client
        self.model = MODELS[self.role]
        self.max_tokens = MAX_TOKENS[self.role]
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
        """Agentic loop: respond with optional tool use."""
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
