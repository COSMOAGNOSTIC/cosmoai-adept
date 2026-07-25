import os
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tavily import TavilyClient
from agent_core.security import safe_path
from agent_core.config import TAVILY_API_KEY


class DigestInput(BaseModel):
    topic: str = Field(
        default="AI agent frameworks",
        description="Topic to pull live search results for",
    )


def _get_news(topic: str) -> str:
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        year = datetime.now().year
        results = client.search(f"{topic} {year}", max_results=5)
        if not results.get("results"):
            return "## News\nNo results found."
        lines = ["## News"]
        for r in results["results"]:
            lines.append(f"- {r['title']}: {r['content'][:200]}")
        return "\n".join(lines)
    except Exception as e:
        return f"## News\nUnavailable: {e}"


def make_digest_tool(sandbox: str):
    """
    Build assemble_digest bound to a single sandbox root, closed over here
    rather than accepted as a model-supplied argument - see files.py's
    make_file_tools() docstring for why.
    """

    @tool(args_schema=DigestInput)
    def assemble_digest(topic: str = "AI agent frameworks") -> str:
        """
        Assemble a scheduled digest: sandbox state (pending items, recent
        activity log) plus live search results on `topic`, into one report.
        Single implementation shared by every scheduled trigger and every
        agent.
        """
        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        sections = [f"# Digest\n{now}\n"]

        pending_path = safe_path(sandbox, "pending.txt")
        if os.path.exists(pending_path):
            with open(pending_path, "r", encoding="utf-8") as f:
                pending = f.read().strip()
            sections.append(f"## Pending Items\n{pending}" if pending else "## Pending Items\nNone.")
        else:
            sections.append("## Pending Items\nNone.")

        log_path = safe_path(sandbox, "activity_log.txt")
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                recent = "".join(f.readlines()[-10:]).strip()
            sections.append(f"## Recent Activity\n{recent}" if recent else "## Recent Activity\nNo log entries yet.")
        else:
            sections.append("## Recent Activity\nNo log entries yet.")

        sections.append(_get_news(topic))
        return "\n\n".join(sections)

    return assemble_digest
