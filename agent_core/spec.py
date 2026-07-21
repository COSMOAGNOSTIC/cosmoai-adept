import datetime
from dataclasses import dataclass, field


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
