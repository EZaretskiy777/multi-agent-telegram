import asyncio
import anthropic
from config import ANTHROPIC_API_KEY, AgentRole, GROUP_CHAT_ID
from agents import OrchestratorAgent, BackendAgent, FrontendAgent, QAAgent, AnalystAgent
from bot.agent_bot import AgentBot
from bot.scheduler import build_scheduler
from core.session import SessionManager


def build_bots(client: anthropic.AsyncAnthropic) -> list[AgentBot]:
    sessions_per_role = {role: SessionManager() for role in AgentRole}

    return [
        AgentBot(AgentRole.ORCHESTRATOR, OrchestratorAgent(client), sessions_per_role[AgentRole.ORCHESTRATOR]),
        AgentBot(AgentRole.BACKEND,      BackendAgent(client),      sessions_per_role[AgentRole.BACKEND]),
        AgentBot(AgentRole.FRONTEND,     FrontendAgent(client),     sessions_per_role[AgentRole.FRONTEND]),
        AgentBot(AgentRole.QA,           QAAgent(client),           sessions_per_role[AgentRole.QA]),
        AgentBot(AgentRole.ANALYST,      AnalystAgent(client),      sessions_per_role[AgentRole.ANALYST]),
    ]


async def run():
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    bots = build_bots(client)

    # Initialize all bots (fetch usernames, start polling)
    await asyncio.gather(*[bot.initialize() for bot in bots])

    orchestrator_bot = bots[0]
    print("✅ All bots started:")
    for bot in bots:
        print(f"   @{bot.username} ({bot.role.value})")

    if not GROUP_CHAT_ID:
        print("\n⚠️  TELEGRAM_GROUP_CHAT_ID not set.")
        print("   1. Create a Telegram group")
        print("   2. Add all 5 bots")
        print("   3. Send /chatid in the group (any bot replies with the ID)")
        print("   4. Add TELEGRAM_GROUP_CHAT_ID=<id> to .env and restart\n")
    else:
        print(f"   Group chat ID: {GROUP_CHAT_ID}")

    # Start daily standup scheduler
    scheduler = build_scheduler(orchestrator_bot)
    scheduler.start()
    print(f"⏰ Daily standup scheduled at {__import__('config').STANDUP_TIME}")

    print("\nRunning. Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()  # run forever
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown(wait=False)
        await asyncio.gather(*[bot.shutdown() for bot in bots])
        print("Stopped.")


if __name__ == "__main__":
    asyncio.run(run())
