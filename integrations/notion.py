import httpx
from config import NOTION_API_KEY, NOTION_PARENT_PAGE_ID

BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def _text_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }


async def create_project_page(project_name: str) -> dict:
    """Create a root documentation page for a new project."""
    body = {
        "parent": {"page_id": NOTION_PARENT_PAGE_ID},
        "properties": {
            "title": {"title": [{"text": {"content": f"📁 {project_name}"}}]}
        },
        "children": [_text_block(f"Документация проекта {project_name}")],
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BASE}/pages", headers=HEADERS, json=body)
        r.raise_for_status()
        data = r.json()
        return {"id": data.get("id", ""), "url": data.get("url", "")}


async def create_page(title: str, content: str, parent_id: str = "") -> dict:
    """Create a documentation page. Uses project page as parent if provided."""
    pid = parent_id or NOTION_PARENT_PAGE_ID
    chunks = [content[i : i + 2000] for i in range(0, len(content), 2000)]
    children = [_text_block(chunk) for chunk in chunks[:10]]

    body = {
        "parent": {"page_id": pid},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
        },
        "children": children,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BASE}/pages", headers=HEADERS, json=body)
        r.raise_for_status()
        data = r.json()
        return {"id": data.get("id", ""), "url": data.get("url", "")}


async def search_pages(query: str) -> list[dict]:
    body = {
        "query": query,
        "filter": {"property": "object", "value": "page"},
        "page_size": 5,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BASE}/search", headers=HEADERS, json=body)
        r.raise_for_status()
        results = r.json().get("results", [])

    pages = []
    for p in results:
        props = p.get("properties", {})
        title_prop = props.get("title", props.get("Name", {}))
        title_list = title_prop.get("title", [])
        title = title_list[0]["plain_text"] if title_list else "Без названия"
        pages.append({"id": p["id"], "title": title, "url": p.get("url", "")})
    return pages


def format_pages(pages: list[dict]) -> str:
    if not pages:
        return "Страниц не найдено."
    return "\n".join(f"• {p['title']}\n  {p['url']}" for p in pages)
