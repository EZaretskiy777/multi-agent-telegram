import base64
import httpx
from config import GITHUB_TOKEN

BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def _get(url: str, params: dict = None) -> dict | list:
    async with httpx.AsyncClient(timeout=15) as client:
        for branch in ("main", "master"):
            p = dict(params or {})
            if "ref" not in p:
                p["ref"] = branch
            r = await client.get(url, headers=HEADERS, params=p)
            if r.status_code != 404:
                r.raise_for_status()
                return r.json()
        r.raise_for_status()
        return r.json()


async def read_file(repo: str, path: str) -> str:
    data = await _get(f"{BASE}/repos/{repo}/contents/{path}")
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content


async def list_dir(repo: str, path: str = "") -> list[dict]:
    items = await _get(f"{BASE}/repos/{repo}/contents/{path}")
    return [
        {"name": i["name"], "type": i["type"], "path": i["path"]}
        for i in items
    ]


async def list_prs(repo: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{BASE}/repos/{repo}/pulls",
            headers=HEADERS,
            params={"state": "open", "per_page": 10},
        )
        r.raise_for_status()
    return [
        {
            "number": p["number"],
            "title":  p["title"],
            "url":    p["html_url"],
            "author": p["user"]["login"],
        }
        for p in r.json()
    ]


async def list_issues(repo: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{BASE}/repos/{repo}/issues",
            headers=HEADERS,
            params={"state": "open", "per_page": 10},
        )
        r.raise_for_status()
    return [
        {"number": i["number"], "title": i["title"], "url": i["html_url"]}
        for i in r.json()
        if "pull_request" not in i
    ]
