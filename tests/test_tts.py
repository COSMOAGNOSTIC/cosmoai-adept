from agent_core.tools.tts import make_tts_tool


def test_tts_tool_does_not_accept_a_sandbox_argument(tmp_path):
    text_to_speech = make_tts_tool(str(tmp_path))
    field_names = set(text_to_speech.args_schema.model_fields.keys())
    assert "sandbox" not in field_names


def test_tts_failure_is_graceful(tmp_path):
    # No ELEVENLABS_API_KEY configured in CI - the client call fails and
    # the tool should return a message, not raise.
    text_to_speech = make_tts_tool(str(tmp_path))
    result = text_to_speech.invoke({"text": "hello", "filename": "out.mp3"})
    assert "TTS failed" in result
