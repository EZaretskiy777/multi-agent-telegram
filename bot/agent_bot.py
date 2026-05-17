import asyncio
import re
import anthropic
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

from config import AgentRole, TELEGRAM_TOKENS, GROUP_CHAT_ID, ANTHROPIC_API_KEY
from core.session import SessionManager

# Shared registry: role → @username (populated at startup)
BOT_USERNAMES: dict[AgentRole, str] = {}

ROLE_DISPLAY = {
    AgentRole.ORCHESTRATOR: "🎯 Оркестратор",
    AgentRole.BACKEND:      "⚙️ Backend",
    AgentRole.FRONTEND:     "🎨 Frontend",
    AgentRole.QA:           "🧪 QA",
    AgentRole.ANALYST:      "📊 Аналитик",
}

CHUNK = 4000


def _split(text: str) -> list[str]:
    return [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]


def _md_to_html(text: str) -> str:
    """Convert Claude's markdown to Telegram HTML."""
    # Escape HTML special chars
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Fenced code blocks (``` ... ```)
    text = re.sub(
        r"```(?:\w+)?\n?(.*?)```",
        lambda m: f"<pre><code>{m.group(1).rstrip()}</code></pre>",
        text,
        flags=re.DOTALL,
    )
    # Inline code
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    # Italic *text* (only single asterisk, not inside words)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    return text


class AgentBot:
    def __init__(self, role: AgentRole, claude_agent, sessions: SessionManager):
        self.role = role
        self.agent = claude_agent
        self.sessions = sessions
        self.username: str = ""
        self.app = Application.builder().token(TELEGRAM_TOKENS[role]).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start",  self._cmd_start))
        self.app.add_handler(CommandHandler("chatid", self._cmd_chatid))
        self.app.add_handler(CommandHandler("tasks",  self._cmd_tasks))
        self.app.add_handler(CommandHandler("clear",  self._cmd_clear))
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._on_message,
            )
        )

    # ── Commands ──────────────────────────────────────────────────────────────

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        name = ROLE_DISPLAY[self.role]
        await update.message.reply_text(
            f"Привет! Я {name}.\n"
            f"Добавь меня в группу и обращайся через @{self.username}."
        )

    async def _cmd_chatid(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"<code>{update.effective_chat.id}</code>", parse_mode="HTML"
        )

    async def _cmd_tasks(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from integrations import linear
        await update.message.chat.send_action(ChatAction.TYPING)
        issues = await linear.get_active_issues()
        text = linear.format_issues(issues)
        for chunk in _split(text):
            await update.message.reply_text(chunk)

    async def _cmd_clear(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        self.sessions.clear(update.effective_chat.id)
        await update.message.reply_text("🗑 История очищена.")

    # ── Message handler ───────────────────────────────────────────────────────

    async def _on_message(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        chat_id = update.effective_chat.id

        # In groups: only respond when mentioned (or orchestrator when no bot mentioned)
        if update.effective_chat.type in ("group", "supergroup"):
            if not await self._should_respond(update):
                return

        user_text = self._clean_text(update)
        if not user_text:
            return

        await update.message.chat.send_action(ChatAction.TYPING)

        # Prepend active project context to the message
        from core.project import project_manager
        project = project_manager.get_active(chat_id)
        if project:
            ctx_line = f"[Проект: {project.name}"
            if project.github_repo:
                ctx_line += f" | GitHub: {project.github_repo}"
            ctx_line += "]"
            stored_text = f"{ctx_line}\n{user_text}"
        else:
            stored_text = user_text

        self.sessions.add(chat_id, "user", stored_text)
        messages = self.sessions.get(chat_id)

        try:
            reply = await self.agent.respond(messages, chat_id=chat_id)
        except Exception as e:
            reply = f"Ошибка: {e}"

        self.sessions.add(chat_id, "assistant", reply)

        html = _md_to_html(reply)
        for chunk in _split(html):
            await update.message.reply_text(chunk, parse_mode="HTML")

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _should_respond(self, update: Update) -> bool:
        """Decide whether this bot should handle the group message."""
        mentioned_usernames = self._mentioned_usernames(update)

        if self.username.lower() in mentioned_usernames:
            return True  # explicitly mentioned

        if self.role == AgentRole.ORCHESTRATOR:
            # Orchestrator handles messages not addressed to any specific bot
            other_usernames = {
                u.lower()
                for r, u in BOT_USERNAMES.items()
                if r != AgentRole.ORCHESTRATOR
            }
            return not (mentioned_usernames & other_usernames)

        return False

    @staticmethod
    def _mentioned_usernames(update: Update) -> set[str]:
        result = set()
        if not update.message or not update.message.entities:
            return result
        text = update.message.text or ""
        for entity in update.message.entities:
            if entity.type == "mention":
                mention = text[entity.offset : entity.offset + entity.length]
                result.add(mention.lstrip("@").lower())
        return result

    def _clean_text(self, update: Update) -> str:
        """Remove all bot @mentions from the message text."""
        text = update.message.text or ""
        entities = update.message.entities or []
        # Remove mention entities in reverse order to preserve offsets
        for entity in sorted(entities, key=lambda e: e.offset, reverse=True):
            if entity.type == "mention":
                text = text[: entity.offset] + text[entity.offset + entity.length :]
        return text.strip()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self):
        await self.app.initialize()
        me = await self.app.bot.get_me()
        self.username = me.username
        BOT_USERNAMES[self.role] = me.username
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

    async def shutdown(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_to_group(self, text: str):
        """Push a message to the configured group chat."""
        if not GROUP_CHAT_ID:
            return
        html = _md_to_html(text)
        for chunk in _split(html):
            await self.app.bot.send_message(chat_id=GROUP_CHAT_ID, text=chunk, parse_mode="HTML")
