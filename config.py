import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

MODELS = {
    "orchestrator": "claude-haiku-4-5",
    "backend":      "claude-sonnet-4-6",
    "frontend":     "claude-sonnet-4-6",
    "qa":           "claude-sonnet-4-6",
    "analyst":      "claude-opus-4-7",
}

MAX_TOKENS = {
    "orchestrator": 1024,
    "backend":      8192,
    "frontend":     8192,
    "qa":           4096,
    "analyst":      16000,
}


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    BACKEND      = "backend"
    FRONTEND     = "frontend"
    QA           = "qa"
    ANALYST      = "analyst"


ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

TELEGRAM_TOKENS: dict[AgentRole, str] = {
    AgentRole.ORCHESTRATOR: os.environ["TELEGRAM_TOKEN_ORCHESTRATOR"],
    AgentRole.BACKEND:      os.environ["TELEGRAM_TOKEN_BACKEND"],
    AgentRole.FRONTEND:     os.environ["TELEGRAM_TOKEN_FRONTEND"],
    AgentRole.QA:           os.environ["TELEGRAM_TOKEN_QA"],
    AgentRole.ANALYST:      os.environ["TELEGRAM_TOKEN_ANALYST"],
}

# Set after the group is created and bots are added
GROUP_CHAT_ID: int = int(os.getenv("TELEGRAM_GROUP_CHAT_ID", "0"))

LINEAR_API_KEY        = os.environ["LINEAR_API_KEY"]
NOTION_API_KEY        = os.environ["NOTION_API_KEY"]
NOTION_PARENT_PAGE_ID = os.environ["NOTION_PARENT_PAGE_ID"]

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Daily standup time in HH:MM (24h, server local time)
STANDUP_TIME = os.getenv("STANDUP_TIME", "09:00")
