from enum import Enum

# Model tiering — cheapest model that can handle each role
MODELS = {
    "orchestrator": "claude-haiku-4-5",   # $1/1M — routing only
    "backend":      "claude-sonnet-4-6",  # $3/1M — code generation
    "frontend":     "claude-sonnet-4-6",  # $3/1M — UI/UX code
    "qa":           "claude-sonnet-4-6",  # $3/1M — test writing
    "analyst":      "claude-opus-4-7",    # $5/1M — complex analysis
}

MAX_TOKENS = {
    "orchestrator": 512,    # Short routing decisions
    "backend":      8192,
    "frontend":     8192,
    "qa":           4096,
    "analyst":      16000,  # Opus with thinking
}

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    BACKEND      = "backend"
    FRONTEND     = "frontend"
    QA           = "qa"
    ANALYST      = "analyst"
