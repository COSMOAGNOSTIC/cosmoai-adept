import datetime
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentSpec:
    """
    Everything that makes one agent different from another.
    build_agent() and build_bot() consume this - nothing else varies.
    """
    name: str
    system_prompt: str
    tools: list
    sandbox: str
    model: str = "claude-sonnet-4-6"

    # Optional - not all agents have voice, scheduling, or Discord
    voice_id: str | None = None
    allowed_channels: set[int] = field(default_factory=set)
    brief_channel: int | None = None
    brief_time: datetime.time | None = None

    # Backend selection - "anthropic" (default) or "local" for an
    # OpenAI-compatible local server (e.g. LM Studio). See config.py's
    # LOCAL_LLM_BASE_URL and ARCHITECTURE.md's Local Backend section.
    backend: str = "anthropic"
    local_base_url: str | None = None  # falls back to config.LOCAL_LLM_BASE_URL
    local_api_key: str = "not-needed"  # most local servers ignore this

    # Human-in-the-loop: tool names in this set pause for approval before
    # they run. approval_hook(tool_name, args) -> bool decides; if None,
    # falls back to a blocking terminal prompt (see agent_core/approvals.py) -
    # fine for a CLI entrypoint, wrong for anything unattended.
    approval_required: set[str] = field(default_factory=set)
    approval_hook: Callable[[str, dict[str, Any]], bool] | None = None
