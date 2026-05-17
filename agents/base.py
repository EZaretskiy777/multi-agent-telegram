import anthropic
from config import MODELS, MAX_TOKENS

# ── Tool definitions ──────────────────────────────────────────────────────────

AGENT_TOOLS = [
    # Linear
    {
        "name": "create_linear_issue",
        "description": (
            "Создать задачу в Linear. Если активен проект — задача привязывается к нему. "
            "Используй когда нужно зафиксировать задачу, баг или фичу."
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
        "description": "Получить список активных задач из Linear (только текущего проекта если он задан).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # Notion
    {
        "name": "create_notion_page",
        "description": (
            "Создать страницу документации в Notion. "
            "Если активен проект — страница создаётся в его папке."
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
    # Project management
    {
        "name": "create_project",
        "description": (
            "Создать новый проект: регистрирует его в системе, создаёт проект в Linear "
            "и папку документации в Notion. Автоматически переключается на новый проект."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string", "description": "Название проекта"},
                "github_repo": {"type": "string", "description": "GitHub репозиторий (owner/repo), опционально"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "switch_project",
        "description": "Переключиться на существующий проект по имени.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Название проекта"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_projects",
        "description": "Показать список всех проектов.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_current_project",
        "description": "Показать текущий активный проект и его реквизиты.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # GitHub
    {
        "name": "read_github_file",
        "description": "Прочитать содержимое файла из GitHub репозитория активного проекта.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь к файлу (например: src/main.py)"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_github_dir",
        "description": "Показать файлы в директории GitHub репозитория активного проекта.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь к директории (пусто = корень репозитория)"}
            },
            "required": [],
        },
    },
    {
        "name": "list_github_prs",
        "description": "Показать открытые Pull Requests в репозитории активного проекта.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_github_issues",
        "description": "Показать открытые Issues в репозитории активного проекта.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # Workspace / code execution
    {
        "name": "write_file",
        "description": (
            "Создать или перезаписать файл в рабочей директории активного проекта на сервере. "
            "Используй для записи кода, конфигов и других файлов."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "Относительный путь к файлу (например: src/main.py)"},
                "content": {"type": "string", "description": "Содержимое файла"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_workspace_file",
        "description": "Прочитать файл из рабочей директории активного проекта на сервере.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Относительный путь к файлу"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_workspace_files",
        "description": "Показать структуру файлов в рабочей директории активного проекта на сервере.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "execute_bash",
        "description": (
            "Выполнить bash-команду в рабочей директории активного проекта на сервере. "
            "Используй для установки зависимостей, запуска тестов, сборки проекта и т.д."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell-команда для выполнения"},
                "timeout": {"type": "integer", "description": "Таймаут в секундах (по умолчанию 60, максимум 300)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "git_push",
        "description": (
            "Зафиксировать все изменения в рабочей директории и запушить в GitHub репозиторий проекта. "
            "Выполняет git add -A, git commit, git push."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Сообщение коммита"}
            },
            "required": ["message"],
        },
    },
]


# ── Tool executor ─────────────────────────────────────────────────────────────

async def execute_tool(name: str, args: dict, chat_id: int = 0) -> str:
    from core.project import project_manager
    from integrations import linear, notion, github, executor

    project = project_manager.get_active(chat_id)

    # ── Linear ────────────────────────────────────────────────────────────────
    if name == "create_linear_issue":
        pid = project.linear_project_id if project else ""
        result = await linear.create_issue(args["title"], args.get("description", ""), project_id=pid)
        if "error" in result:
            return f"Ошибка Linear: {result['error']}"
        return f"Задача создана: [{result.get('identifier')}] {result.get('title')}\n{result.get('url')}"

    if name == "get_linear_issues":
        pid = project.linear_project_id if project else ""
        issues = await linear.get_active_issues(project_id=pid)
        return linear.format_issues(issues)

    # ── Notion ────────────────────────────────────────────────────────────────
    if name == "create_notion_page":
        parent_id = project.notion_page_id if project else ""
        result = await notion.create_page(args["title"], args["content"], parent_id=parent_id)
        return f"Страница создана: {result.get('url')}"

    if name == "search_notion":
        pages = await notion.search_pages(args["query"])
        return notion.format_pages(pages)

    # ── Project management ────────────────────────────────────────────────────
    if name == "create_project":
        pname       = args["name"]
        github_repo = args.get("github_repo", "")
        # If user gave just repo name without owner, prepend default owner
        if github_repo and "/" not in github_repo:
            from config import GITHUB_OWNER
            if GITHUB_OWNER:
                github_repo = f"{GITHUB_OWNER}/{github_repo}"

        linear_result = await linear.create_project(pname)
        notion_result = await notion.create_project_page(pname)

        new_project = project_manager.create(
            pname,
            github_repo=github_repo,
            linear_project_id=linear_result.get("id", ""),
            linear_project_url=linear_result.get("url", ""),
            notion_page_id=notion_result.get("id", ""),
            notion_page_url=notion_result.get("url", ""),
        )
        if chat_id:
            project_manager.set_active(chat_id, pname)

        lines = [f"✅ Проект «{pname}» создан и активирован"]
        if new_project.linear_project_url:
            lines.append(f"Linear: {new_project.linear_project_url}")
        if new_project.notion_page_url:
            lines.append(f"Notion: {new_project.notion_page_url}")
        if github_repo:
            lines.append(f"GitHub: https://github.com/{github_repo}")
        return "\n".join(lines)

    if name == "switch_project":
        pname = args["name"]
        if project_manager.set_active(chat_id, pname):
            p = project_manager.get(pname)
            return f"✅ Переключились на проект «{p.name}»"
        all_names = ", ".join(p.name for p in project_manager.list_all())
        return f"Проект «{pname}» не найден. Доступные: {all_names or 'нет проектов'}"

    if name == "list_projects":
        projects = project_manager.list_all()
        if not projects:
            return "Нет проектов. Создай первый: «создай проект X»"
        lines = []
        for p in projects:
            marker = "→" if project and project.name == p.name else "•"
            repo = f" ({p.github_repo})" if p.github_repo else ""
            lines.append(f"{marker} {p.name}{repo}")
        return "\n".join(lines)

    if name == "get_current_project":
        if not project:
            return "Нет активного проекта. Напиши «создай проект X» или «работаем с проектом Y»"
        lines = [f"Активный проект: {project.name}"]
        if project.github_repo:
            lines.append(f"GitHub: {project.github_repo}")
        if project.linear_project_url:
            lines.append(f"Linear: {project.linear_project_url}")
        if project.notion_page_url:
            lines.append(f"Notion: {project.notion_page_url}")
        return "\n".join(lines)

    # ── GitHub ────────────────────────────────────────────────────────────────
    if name in ("read_github_file", "list_github_dir", "list_github_prs", "list_github_issues"):
        if not project or not project.github_repo:
            return "Нет активного проекта с GitHub репозиторием."
        repo = project.github_repo
        try:
            if name == "read_github_file":
                content = await github.read_file(repo, args["path"])
                return content[:4000]
            if name == "list_github_dir":
                items = await github.list_dir(repo, args.get("path", ""))
                lines = [f"{'📁' if i['type'] == 'dir' else '📄'} {i['path']}" for i in items]
                return "\n".join(lines) or "Директория пуста"
            if name == "list_github_prs":
                prs = await github.list_prs(repo)
                if not prs:
                    return "Нет открытых PR"
                return "\n".join(
                    f"• PR #{p['number']}: {p['title']} ({p['author']})\n  {p['url']}" for p in prs
                )
            if name == "list_github_issues":
                issues = await github.list_issues(repo)
                if not issues:
                    return "Нет открытых Issues"
                return "\n".join(
                    f"• #{i['number']}: {i['title']}\n  {i['url']}" for i in issues
                )
        except Exception as e:
            return f"Ошибка GitHub: {e}"

    # ── Workspace / code execution ────────────────────────────────────────────
    if name in ("write_file", "read_workspace_file", "list_workspace_files", "execute_bash", "git_push"):
        if not project:
            return "Нет активного проекта. Создай или переключись на проект перед выполнением команд."
        pname = project.name

        if name == "write_file":
            return executor.write_file(pname, args["path"], args["content"])

        if name == "read_workspace_file":
            return executor.read_file(pname, args["path"])

        if name == "list_workspace_files":
            return executor.list_files(pname)

        if name == "execute_bash":
            timeout = min(int(args.get("timeout", 60)), 300)
            cwd = executor.ensure_dir(pname)
            return await executor.run(args["command"], cwd, timeout=timeout)

        if name == "git_push":
            from config import GITHUB_TOKEN
            if not project.github_repo:
                return "У активного проекта не задан GitHub репозиторий."
            if not GITHUB_TOKEN:
                return "GITHUB_TOKEN не задан в конфиге."
            cwd = executor.ensure_dir(pname)
            repo = project.github_repo
            remote_url = f"https://{GITHUB_TOKEN}@github.com/{repo}.git"
            cmds = [
                "git init -b main 2>/dev/null || true",
                f"git remote set-url origin {remote_url} 2>/dev/null || git remote add origin {remote_url}",
                "git add -A",
                f"git commit -m {repr(args['message'])}",
                "git push -u origin main",
            ]
            output_parts = []
            for cmd in cmds:
                out = await executor.run(cmd, cwd, timeout=60)
                output_parts.append(out)
                if out.startswith("[exit") and "nothing to commit" not in out:
                    break
            return "\n".join(output_parts)

    return f"Неизвестный инструмент: {name}"


# ── Base agent ────────────────────────────────────────────────────────────────

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
