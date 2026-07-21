import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from elevenlabs.client import ElevenLabs
from agent_core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from agent_core.security import safe_path


class TTSInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")
    text: str = Field(description="Text to convert to speech")
    filename: str = Field(description="Output filename, relative to sandbox (e.g. 'output.mp3')")
    speed: float = Field(default=1.2, description="Playback speed multiplier, 0.5-2.0")


@tool(args_schema=TTSInput)
def text_to_speech(sandbox: str, text: str, filename: str, speed: float = 1.2) -> str:
    """Convert text to speech and save as an mp3 in the agent's sandbox."""
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    output_path = safe_path(sandbox, filename)
    try:
        audio = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_monolingual_v1",
            voice_settings={"speed": speed},
        )
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        return f"Audio saved: {filename}"
    except Exception as e:
        return f"TTS failed: {e}"
