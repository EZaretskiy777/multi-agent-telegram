# Multi-Agent Telegram Bot

Telegram-группа с командой AI-агентов. Каждый агент — отдельный бот со своей специализацией. Обращайся к нужному через @mention, или пиши без упоминания — ответит Оркестратор.

## Агенты

| Бот | Модель | Роль |
|-----|--------|------|
| @OrchestratorBot | Claude Haiku 4.5 | Координатор, дейли, общие вопросы |
| @BackendBot | Claude Sonnet 4.6 | API, базы данных, Python, Go |
| @FrontendBot | Claude Sonnet 4.6 | React, CSS, UI/UX |
| @QABot | Claude Sonnet 4.6 | Тесты, автоматизация, баг-репорты |
| @AnalystBot | Claude Opus 4.7 | Требования, архитектура, PRD |

## Что умеют агенты

- Отвечают на @упоминание в группе
- Создают задачи в **Linear** (`"создай задачу: ..."`)
- Создают документацию в **Notion** (`"задокументируй это..."`)
- Ежедневный **дейли** по расписанию — статус задач из Linear
- Помнят историю диалога в рамках сессии

## Оптимизация токенов

- **Разные модели** — Haiku для координации, Sonnet для работы, Opus только для глубокого анализа
- **Prompt caching** — повторные запросы к тому же агенту стоят ~10% от обычной цены
- **Adaptive thinking** — только у Аналитика (Opus), только когда нужно

## Установка

```bash
git clone https://github.com/EZaretskiy777/multi-agent-telegram.git
cd multi-agent-telegram
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Заполни .env своими ключами
python3 main.py
```

## Настройка шаг за шагом

### 1. Создать 5 ботов в @BotFather
```
/newbot → выбери имя → получи токен
```
Для каждого бота отключи group privacy:
```
/setprivacy → выбери бота → Disable
```

### 2. Заполнить .env
```env
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_TOKEN_ORCHESTRATOR=...
TELEGRAM_TOKEN_BACKEND=...
TELEGRAM_TOKEN_FRONTEND=...
TELEGRAM_TOKEN_QA=...
TELEGRAM_TOKEN_ANALYST=...
LINEAR_API_KEY=...
NOTION_API_KEY=...
NOTION_PARENT_PAGE_ID=...
```

### 3. Запустить (пока без GROUP_CHAT_ID)
```bash
python3 main.py
```

### 4. Получить ID группы
1. Создай Telegram-группу
2. Добавь все 5 ботов
3. Напиши в группе `/chatid` — любой бот ответит ID
4. Добавь в `.env`: `TELEGRAM_GROUP_CHAT_ID=-100xxxxxxxxx`
5. Перезапусти: `python3 main.py`

## Команды в чате

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие бота |
| `/chatid` | Показать ID текущего чата |
| `/tasks` | Показать активные задачи из Linear |
| `/clear` | Очистить историю диалога |

## Структура проекта

```
multi-agent-telegram/
├── agents/
│   ├── base.py          # BaseAgent: AsyncAnthropic + tool use + prompt caching
│   ├── orchestrator.py  # Координатор и ведущий дейли
│   ├── backend.py       # Backend-специалист
│   ├── frontend.py      # Frontend-специалист
│   ├── qa.py            # QA-специалист
│   └── analyst.py       # Аналитик: Opus + adaptive thinking
├── integrations/
│   ├── linear.py        # Linear GraphQL API (задачи)
│   └── notion.py        # Notion REST API (документация)
├── bot/
│   ├── agent_bot.py     # AgentBot: mention detection, handlers, lifecycle
│   └── scheduler.py     # APScheduler: ежедневный дейли
├── core/
│   └── session.py       # История диалога per chat_id
├── config.py            # Модели, токены, переменные окружения
├── main.py              # Запуск 5 ботов параллельно через asyncio
└── requirements.txt
```
