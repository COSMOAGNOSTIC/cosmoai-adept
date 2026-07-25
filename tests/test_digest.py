from unittest.mock import patch

from agent_core.tools.digest import make_digest_tool


def test_digest_includes_pending_and_activity(tmp_path):
    sandbox = str(tmp_path)
    (tmp_path / "pending.txt").write_text("buy milk\n")
    (tmp_path / "activity_log.txt").write_text("[2026-01-01 00:00:00] did a thing\n")

    assemble_digest = make_digest_tool(sandbox)
    with patch("agent_core.tools.digest._get_news", return_value="## News\nstubbed"):
        out = assemble_digest.invoke({})

    assert "buy milk" in out
    assert "did a thing" in out
    assert "stubbed" in out


def test_digest_handles_empty_sandbox(tmp_path):
    assemble_digest = make_digest_tool(str(tmp_path))
    with patch("agent_core.tools.digest._get_news", return_value="## News\nstubbed"):
        out = assemble_digest.invoke({})

    assert "None." in out
    assert "No log entries yet." in out


def test_digest_news_failure_is_graceful():
    with patch("agent_core.tools.digest.TavilyClient") as mock_client:
        mock_client.side_effect = RuntimeError("boom")
        from agent_core.tools.digest import _get_news

        result = _get_news("anything")

    assert "Unavailable" in result


def test_digest_tool_does_not_accept_a_sandbox_argument(tmp_path):
    assemble_digest = make_digest_tool(str(tmp_path))
    field_names = set(assemble_digest.args_schema.model_fields.keys())
    assert "sandbox" not in field_names
