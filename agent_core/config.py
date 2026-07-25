import os
import sys
from dotenv import load_dotenv

_secrets = os.environ.get("AGENT_SECRETS_DIR", os.path.join(os.getcwd(), "secrets"))
_env_file = os.path.join(_secrets, ".env")
if not os.path.exists(_env_file):
    # An independent code review flagged this as a silent-misconfiguration
    # risk: if cwd isn't the repo root and AGENT_SECRETS_DIR is unset,
    # load_dotenv() below fails silently and every *_API_KEY constant ends
    # up None -- surfacing only as a confusing auth error deep inside a
    # model call, far from the actual cause. This doesn't change behavior
    # (still no hard failure -- a fresh clone with no secrets configured
    # yet is a normal, supported state), it just makes the cause visible
    # immediately instead of at first API-call failure.
    print(
        f"agent_core.config: no .env found at {_env_file!r} -- "
        f"API-key-dependent features will be unavailable until one exists "
        f"(or AGENT_SECRETS_DIR points somewhere else).",
        file=sys.stderr,
    )
load_dotenv(_env_file)

SECRETS_DIR = _secrets


def sandbox_path(agent_name: str) -> str:
    """Resolve an agent's sandbox directory from an env var, e.g. SANDBOX_<NAME>."""
    env_key = f"SANDBOX_{agent_name.upper()}"
    return os.getenv(env_key, os.path.join(os.getcwd(), "sandboxes", agent_name.lower()))


def memory_path(agent_name: str) -> str:
    """
    Resolve an agent's conversation-memory directory from an env var, e.g.
    MEMORY_<NAME> -- deliberately separate from `sandbox_path()`.

    An independent code review found `build_agent()` was pointing the
    SQLite checkpointer at the agent's *sandbox* directory -- the same
    directory its file tools are bound to via `safe_path()`. That means
    the model could read (leaking other threads'/conversations' history)
    or corrupt its own checkpoint DB using its own ordinary, sandboxed
    file tools, despite memory.py's docstring claiming the DB is "never in
    secrets, never in cloud sync" (true) without mentioning it was
    reachable by the model itself (not true, and the actual problem).
    Memory now defaults to a directory that is never a tool sandbox root
    for any agent.
    """
    env_key = f"MEMORY_{agent_name.upper()}"
    return os.getenv(env_key, os.path.join(os.getcwd(), "agent_memory", agent_name.lower()))


def discord_channel_id(agent_name: str) -> int:
    """
    Look up an agent's allowed Discord channel id, e.g. <NAME>_CHANNEL_ID.
    Returns 0 (meaning "no restriction configured") if the env var is unset
    or isn't a valid integer, rather than letting a typo'd env value raise
    an uncaught ValueError and crash the entrypoint at startup.
    """
    raw = os.getenv(f"{agent_name.upper()}_CHANNEL_ID", "0")
    try:
        return int(raw)
    except ValueError:
        return 0


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Local, OpenAI-compatible LLM server (e.g. LM Studio) - used when an
# AgentSpec sets backend="local". Lets the whole framework run against a
# GPU-offloaded local model with zero API cost and zero network egress.
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")


def discord_token(agent_name: str) -> str | None:
    """Look up an agent's Discord bot token, e.g. DISCORD_BOT_TOKEN_<NAME>."""
    return os.getenv(f"DISCORD_BOT_TOKEN_{agent_name.upper()}")
