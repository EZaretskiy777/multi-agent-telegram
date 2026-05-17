# Multi-Agent Telegram Bot

A Telegram bot that routes user requests to specialized AI agents powered by Claude.

## Agents

| Agent | Model | Role |
|-------|-------|------|
| Orchestrator | Claude Haiku 4.5 | Routes requests to the right specialist |
| Backend | Claude Sonnet 4.6 | APIs, databases, Python, Go, architecture |
| Frontend | Claude Sonnet 4.6 | React, CSS, UI/UX, accessibility |
| QA | Claude Sonnet 4.6 | Tests, automation, bug reports |
| Analyst | Claude Opus 4.7 | Requirements, system design, PRD |

## Cost optimizations

- **Model tiering** — cheapest model (Haiku) for routing, heavier models only for actual work
- **Prompt caching** — `cache_control: ephemeral` on all system prompts; after warm-up, cached tokens cost ~10% of normal input price
- **Adaptive thinking** — only on the Analyst (Opus), only when needed
- **Streaming** — long responses stream to avoid timeouts

## Setup

```bash
# 1. Clone and install dependencies
git clone https://github.com/EZaretskiy777/multi-agent-telegram.git
cd multi-agent-telegram
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add your Anthropic API key and Telegram bot token

# 3. Run
python main.py
```

## Bot commands

- `/start` — welcome message with agent overview
- `/clear` — reset conversation history for current chat

## Project structure

```
multi-agent-telegram/
├── agents/
│   ├── base.py          # BaseAgent with prompt caching
│   ├── orchestrator.py  # Haiku router → JSON routing decision
│   ├── backend.py       # Sonnet — server-side specialist
│   ├── frontend.py      # Sonnet — UI/UX specialist
│   ├── qa.py            # Sonnet — QA specialist
│   └── analyst.py       # Opus + adaptive thinking — analysis
├── bot/
│   └── handler.py       # Telegram handlers, streaming, session wiring
├── core/
│   └── session.py       # Per-chat conversation history
├── config.py            # Model IDs, token limits, AgentRole enum
├── main.py              # Entry point
└── requirements.txt
```
