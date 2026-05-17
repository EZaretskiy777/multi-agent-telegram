import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import STANDUP_TIME, GROUP_CHAT_ID
from integrations import linear


async def run_standup(orchestrator_bot) -> None:
    """Fetch active tasks from Linear and post a standup report to the group."""
    if not GROUP_CHAT_ID:
        return

    issues = await linear.get_active_issues()

    header = "☀️ *Ежедневный дейли*\n\n"

    if not issues:
        await orchestrator_bot.send_to_group(header + "Нет активных задач. Отличный день!")
        return

    # Group by status
    by_status: dict[str, list[dict]] = {}
    for issue in issues:
        state = issue.get("state", {}).get("name", "Unknown")
        by_status.setdefault(state, []).append(issue)

    lines = [header]
    for status, items in by_status.items():
        lines.append(f"*{status}* ({len(items)})")
        for issue in items:
            assignee = (issue.get("assignee") or {}).get("name", "—")
            lines.append(f"  • [{issue['identifier']}] {issue['title']} → {assignee}")
        lines.append("")

    lines.append(f"Всего активных задач: {len(issues)}")
    lines.append("Хорошего дня! 💪")

    text = "\n".join(lines)
    # Send as plain text to avoid markdown parse errors on special chars
    await orchestrator_bot.send_to_group(text.replace("*", ""))


def build_scheduler(orchestrator_bot) -> AsyncIOScheduler:
    hour, minute = map(int, STANDUP_TIME.split(":"))
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_standup,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[orchestrator_bot],
        id="daily_standup",
        replace_existing=True,
    )
    return scheduler
