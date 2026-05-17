import httpx
from config import LINEAR_API_KEY

URL = "https://api.linear.app/graphql"
HEADERS = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json",
}


async def _gql(query: str, variables: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
        r.raise_for_status()
        return r.json().get("data", {})


async def get_team_id() -> str | None:
    data = await _gql("query { teams { nodes { id name } } }")
    nodes = data.get("teams", {}).get("nodes", [])
    return nodes[0]["id"] if nodes else None


async def create_project(name: str) -> dict:
    team_id = await get_team_id()
    if not team_id:
        return {"error": "No Linear team found"}

    mutation = """
    mutation CreateProject($name: String!, $teamId: String!) {
        projectCreate(input: {name: $name, teamIds: [$teamId]}) {
            success
            project { id name url }
        }
    }
    """
    data = await _gql(mutation, {"name": name, "teamId": team_id})
    return data.get("projectCreate", {}).get("project", {})


async def create_issue(title: str, description: str, project_id: str = "") -> dict:
    team_id = await get_team_id()
    if not team_id:
        return {"error": "No Linear team found"}

    if project_id:
        mutation = """
        mutation Create($title: String!, $desc: String!, $team: String!, $project: String!) {
            issueCreate(input: {title: $title, description: $desc, teamId: $team, projectId: $project}) {
                success
                issue { id title url identifier }
            }
        }
        """
        data = await _gql(mutation, {"title": title, "desc": description, "team": team_id, "project": project_id})
    else:
        mutation = """
        mutation Create($title: String!, $desc: String!, $team: String!) {
            issueCreate(input: {title: $title, description: $desc, teamId: $team}) {
                success
                issue { id title url identifier }
            }
        }
        """
        data = await _gql(mutation, {"title": title, "desc": description, "team": team_id})

    return data.get("issueCreate", {}).get("issue", {})


async def get_active_issues(project_id: str = "") -> list[dict]:
    if project_id:
        query = """
        query($projectId: String!) {
            issues(
                filter: {
                    state: { type: { nin: ["completed", "cancelled"] } }
                    project: { id: { eq: $projectId } }
                }
                first: 30
                orderBy: updatedAt
            ) {
                nodes {
                    identifier title url
                    state { name type }
                    priority
                    assignee { name }
                }
            }
        }
        """
        data = await _gql(query, {"projectId": project_id})
    else:
        query = """
        query {
            issues(
                filter: { state: { type: { nin: ["completed", "cancelled"] } } }
                first: 30
                orderBy: updatedAt
            ) {
                nodes {
                    identifier title url
                    state { name type }
                    priority
                    assignee { name }
                }
            }
        }
        """
        data = await _gql(query)

    return data.get("issues", {}).get("nodes", [])


def format_issues(issues: list[dict]) -> str:
    if not issues:
        return "Нет активных задач."

    priority_map = {0: "—", 1: "🔴 Urgent", 2: "🟠 High", 3: "🟡 Medium", 4: "🟢 Low"}
    lines = []
    for issue in issues:
        p = priority_map.get(issue.get("priority", 0), "—")
        state    = issue.get("state", {}).get("name", "?")
        assignee = (issue.get("assignee") or {}).get("name", "не назначена")
        lines.append(
            f"• [{issue['identifier']}] {issue['title']}\n"
            f"  Статус: {state} | Приоритет: {p} | Исполнитель: {assignee}\n"
            f"  {issue.get('url', '')}"
        )
    return "\n\n".join(lines)
