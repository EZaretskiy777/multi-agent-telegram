import os
from dotenv import load_dotenv
from bot import build_app

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]


def main() -> None:
    app = build_app(TELEGRAM_TOKEN, ANTHROPIC_KEY)
    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
