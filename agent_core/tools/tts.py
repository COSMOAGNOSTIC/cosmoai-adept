from langchain_core.tools import tool
from pydantic import BaseModel, Field
from elevenlabs.client import ElevenLabs
from agent_core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from agent_core.security import safe_open, safe_path


class TTSInput(BaseModel):
    text: str = Field(description="Text to convert to speech")
    filename: str = Field(description="Output filename, relative to the agent's sandbox (e.g. 'output.mp3')")
    speed: float = Field(default=1.2, description="Playback speed multiplier, 0.5-2.0")


def make_tts_tool(sandbox: str):
    """
    Build text_to_speech bound to a single sandbox root, closed over here
    rather than accepted as a model-supplied argument - see files.py's
    make_file_tools() docstring for why.
    """

    @tool(args_schema=TTSInput)
    def text_to_speech(text: str, filename: str, speed: float = 1.2) -> str:
        """Convert text to speech and save as an mp3 in the agent's sandbox."""
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        safe_path(sandbox, filename)  # fail fast on a bad filename before spending an API call
        try:
            audio = client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=text,
                model_id="eleven_monolingual_v1",
                voice_settings={"speed": speed},
            )
            with safe_open(sandbox, filename, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            return f"Audio saved: {filename}"
        except Exception as e:
            return f"TTS failed: {e}"

    return text_to_speech
