import anthropic
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

from agents import (
    OrchestratorAgent,
    BackendAgent,
    FrontendAgent,
    QAAgent,
    AnalystAgent,
)
from config import AgentRole
from core import SessionManager

AGENT_EMOJI = {
    AgentRole.BACKEND:  "⚙️",
    AgentRole.FRONTEND: "🎨",
    AgentRole.QA:       "🧪",
    AgentRole.ANALYST:  "📊",
}

TELEGRAM_CHUNK = 4000  # Telegram max message length is 4096


def _agents(client: anthropic.Anthropic) -> dict:
    return {
        AgentRole.BACKEND:  BackendAgent(client),
        AgentRole.FRONTEND: FrontendAgent(client),
        AgentRole.QA:       QAAgent(client),
        AgentRole.ANALYST:  AnalystAgent(client),
    }


async def _send_long(update: Update, text: str) -> None:
    """Split text into Telegram-safe chunks."""
    for i in range(0, len(text), TELEGRAM_CHUNK):
        await update.message.reply_text(text[i : i + TELEGRAM_CHUNK])


def build_app(telegram_token: str, anthropic_api_key: str) -> Application:
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    orchestrator = OrchestratorAgent(client)
    specialists = _agents(client)
    sessions = SessionManager()

    app = Application.builder().token(telegram_token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "👋 Привет! Я мульти-агентный ассистент.\n\n"
            "Просто напиши свой вопрос, и я направлю его нужному специалисту:\n"
            "⚙️ Backend — API, базы данных, Python, Go\n"
            "🎨 Frontend — UI, React, CSS, UX\n"
            "🧪 QA — тесты, автоматизация, баг-репорты\n"
            "📊 Аналитик — требования, архитектура, PRD\n\n"
            "/clear — очистить историю диалога"
        )

    async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        sessions.clear(update.effective_chat.id)
        await update.message.reply_text("🗑 История очищена.")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        user_text = update.message.text

        await update.message.chat.send_action(ChatAction.TYPING)

        # Route to specialist
        role, reason = orchestrator.route(user_text)
        emoji = AGENT_EMOJI.get(role, "🤖")
        await update.message.reply_text(f"{emoji} _{reason}_", parse_mode="Markdown")

        # Build conversation history
        sessions.add(chat_id, "user", user_text)
        messages = sessions.get(chat_id)

        # Stream response
        agent = specialists[role]
        chunks: list[str] = []
        buffer = ""

        await update.message.chat.send_action(ChatAction.TYPING)

        for token in agent.stream(messages):
            buffer += token
            chunks.append(token)

        full_response = "".join(chunks)
        sessions.add(chat_id, "assistant", full_response)

        await _send_long(update, full_response)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
