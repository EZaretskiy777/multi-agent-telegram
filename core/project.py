import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime

_PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "..", "projects.json")


@dataclass
class Project:
    name: str
    github_repo: str = ""
    linear_project_id: str = ""
    linear_project_url: str = ""
    notion_page_id: str = ""
    notion_page_url: str = ""
    created_at: str = ""


class ProjectManager:
    def __init__(self):
        self._projects: dict[str, Project] = {}   # name.lower() → Project
        self._active:   dict[int, str]    = {}    # chat_id → name key
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        path = os.path.abspath(_PROJECTS_FILE)
        if not os.path.exists(path):
            return
        with open(path) as f:
            data = json.load(f)
        self._projects = {k: Project(**v) for k, v in data.get("projects", {}).items()}
        self._active   = {int(k): v for k, v in data.get("active", {}).items()}

    def _save(self):
        path = os.path.abspath(_PROJECTS_FILE)
        with open(path, "w") as f:
            json.dump(
                {
                    "projects": {k: asdict(v) for k, v in self._projects.items()},
                    "active":   {str(k): v for k, v in self._active.items()},
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, name: str, **kwargs) -> Project:
        project = Project(name=name, created_at=datetime.now().isoformat(), **kwargs)
        self._projects[name.lower()] = project
        self._save()
        return project

    def get(self, name: str) -> Project | None:
        return self._projects.get(name.lower())

    def update(self, name: str, **kwargs):
        key = name.lower()
        if key in self._projects:
            for k, v in kwargs.items():
                setattr(self._projects[key], k, v)
            self._save()

    def list_all(self) -> list[Project]:
        return list(self._projects.values())

    # ── Active project per chat ───────────────────────────────────────────────

    def get_active(self, chat_id: int) -> Project | None:
        key = self._active.get(chat_id)
        return self._projects.get(key) if key else None

    def set_active(self, chat_id: int, name: str) -> bool:
        key = name.lower()
        if key not in self._projects:
            return False
        self._active[chat_id] = key
        self._save()
        return True


# Singleton — imported everywhere
project_manager = ProjectManager()
