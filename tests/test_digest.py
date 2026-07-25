from unittest.mock import patch

from agent_core.tools.digest import assemble_digest


def test_digest_includes_pending_and_activity(tmp_path):
    sandbox = str(tmp_path)
    (tmp_path / "pending.txt").write_text("buy milk\n")
    (tmp_path / "activity_log.txt").write_text("[2026-01-01 00:00:00] did a thing\n")

    with patch("agent_core.tools.digest._get_news", return_value="## News\nstubbed"):
        out = assemble_digest.invoke({"sandbox": sandbox})

    assert "buy milk" in out
    assert "did a thing" in out
    assert "stubbed" in out


def test_digest_handles_empty_sandbox(tmp_path):
    with patch("agent_core.tools.digest._get_news", return_value="## News\nstubbed"):
        out = assemble_digest.invoke({"sandbox": str(tmp_path)})

    assert "None." in out
    assert "No log entries yet." in out


def test_digest_news_failure_is_graceful():
    with patch("agent_core.tools.digest.TavilyClient") as mock_client:
        mock_client.side_effect = RuntimeError("boom")
        from agent_core.tools.digest import _get_news

        result = _get_news("anything")

    assert "Unavailable" in result
