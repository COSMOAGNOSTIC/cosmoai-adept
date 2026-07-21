import os
from dotenv import load_dotenv

_secrets = os.environ.get("AGENT_SECRETS_DIR", os.path.join(os.getcwd(), "secrets"))
load_dotenv(os.path.join(_secrets, ".env"))

SECRETS_DIR = _secrets


def sandbox_path(agent_name: str) -> str:
    """Resolve an agent's sandbox directory from an env var, e.g. SANDBOX_<NAME>."""
    env_key = f"SANDBOX_{agent_name.upper()}"
    return os.getenv(env_key, os.path.join(os.getcwd(), "sandboxes", agent_name.lower()))


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def discord_token(agent_name: str) -> str | None:
    """Look up an agent's Discord bot token, e.g. DISCORD_BOT_TOKEN_<NAME>."""
    return os.getenv(f"DISCORD_BOT_TOKEN_{agent_name.upper()}")


def discord_channel_id(agent_name: str) -> int:
    """Look up an agent's allowed Discord channel id, e.g. <NAME>_CHANNEL_ID."""
    return int(os.getenv(f"{agent_name.upper()}_CHANNEL_ID", "0"))
