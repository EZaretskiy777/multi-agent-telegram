import asyncio
import os
from pathlib import Path

WORKSPACE_ROOT = Path("/root/workspace")


def project_dir(project_name: str) -> Path:
    return WORKSPACE_ROOT / project_name.lower().replace(" ", "-")


def ensure_dir(project_name: str) -> Path:
    d = project_dir(project_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


async def run(command: str, cwd: Path, timeout: int = 60) -> str:
    """Execute a shell command and return combined stdout+stderr."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "HOME": "/root"},
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace").strip()
            if proc.returncode != 0:
                return f"[exit {proc.returncode}]\n{output}" if output else f"[exit {proc.returncode}]"
            return output or "(no output)"
        except asyncio.TimeoutError:
            proc.kill()
            return f"[timeout after {timeout}s — command killed]"
    except Exception as e:
        return f"[error: {e}]"


def write_file(project_name: str, rel_path: str, content: str) -> str:
    base = ensure_dir(project_name)
    target = (base / rel_path).resolve()
    # Safety: stay inside workspace
    if not str(target).startswith(str(WORKSPACE_ROOT)):
        return "Error: path escapes workspace"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"✅ Written: {rel_path} ({len(content)} chars)"


def read_file(project_name: str, rel_path: str) -> str:
    base = project_dir(project_name)
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT)):
        return "Error: path escapes workspace"
    if not target.exists():
        return f"File not found: {rel_path}"
    content = target.read_text(encoding="utf-8", errors="replace")
    if len(content) > 6000:
        content = content[:6000] + f"\n\n... [truncated — {len(content)} total chars]"
    return content


def list_files(project_name: str) -> str:
    base = project_dir(project_name)
    if not base.exists():
        return "Workspace not initialised yet. Use execute_bash to set up the project."
    items = []
    for item in sorted(base.rglob("*")):
        if any(p in {".git", "__pycache__", "node_modules", ".venv"} for p in item.parts):
            continue
        rel = item.relative_to(base)
        prefix = "📁" if item.is_dir() else "📄"
        items.append(f"{prefix} {rel}")
    return "\n".join(items[:150]) or "(workspace is empty)"
