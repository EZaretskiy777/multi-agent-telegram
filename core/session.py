from collections import defaultdict
from typing import DefaultDict


MAX_HISTORY = 20  # messages per session (keep context window manageable)


class SessionManager:
    """
    Per-chat conversation history. Each chat_id gets its own message list.
    History is trimmed to MAX_HISTORY to avoid ballooning token costs.
    """

    def __init__(self):
        self._history: DefaultDict[int, list[dict]] = defaultdict(list)

    def add(self, chat_id: int, role: str, content: str) -> None:
        history = self._history[chat_id]
        history.append({"role": role, "content": content})
        # Trim oldest pairs (keep even count for user/assistant alternation)
        if len(history) > MAX_HISTORY:
            trim = len(history) - MAX_HISTORY
            # Always trim in pairs to maintain user/assistant alternation
            trim = trim + (trim % 2)
            self._history[chat_id] = history[trim:]

    def get(self, chat_id: int) -> list[dict]:
        return list(self._history[chat_id])

    def clear(self, chat_id: int) -> None:
        self._history[chat_id] = []
