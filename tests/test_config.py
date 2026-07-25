"""
Tests for agent_core/config.py's path-resolution and env-parsing helpers.

`sandbox_path()` already had informal coverage via other tests exercising
build_agent(); `memory_path()` and the fail-closed `discord_channel_id()`
did not have any, and both were touched by the 2026-07-25 external-review
follow-up round.
"""

import importlib
import os

from agent_core import config


def test_memory_path_defaults_to_a_directory_distinct_from_sandbox_path():
    """
    memory_path() and sandbox_path() must never resolve to the same
    directory for the same agent name -- that's the whole point of
    memory_path() existing (see its docstring / ARCHITECTURE.md Section 4:
    the checkpointer must not live somewhere the model's own sandboxed
    file tools can reach).
    """
    name = "some-agent"
    assert config.memory_path(name) != config.sandbox_path(name)
    assert "agent_memory" in config.memory_path(name)
    assert "sandboxes" in config.sandbox_path(name)


def test_memory_path_respects_env_override(monkeypatch, tmp_path):
    override = str(tmp_path / "custom-memory-root")
    monkeypatch.setenv("MEMORY_MYAGENT", override)
    assert config.memory_path("myagent") == override


def test_discord_channel_id_returns_zero_when_unset():
    assert config.discord_channel_id("no-such-agent-configured") == 0


def test_discord_channel_id_parses_a_valid_value(monkeypatch):
    monkeypatch.setenv("WEATHERBOT_CHANNEL_ID", "123456789")
    assert config.discord_channel_id("weatherbot") == 123456789


def test_discord_channel_id_fails_closed_to_zero_on_a_malformed_value(monkeypatch):
    """
    An independent code review found this raised an uncaught ValueError on
    a non-numeric env value -- a typo'd .env entry would crash the entire
    entrypoint at startup instead of degrading gracefully. Regression test
    for the fix: a malformed value now resolves to 0 ("no restriction"),
    same as unset, rather than raising.
    """
    monkeypatch.setenv("WEATHERBOT_CHANNEL_ID", "not-a-number")
    assert config.discord_channel_id("weatherbot") == 0


def test_missing_env_file_warns_on_stderr_instead_of_failing_silently(tmp_path, capsys, monkeypatch):
    """
    An independent code review flagged the original silent-misconfiguration
    risk: with no .env file and no explicit AGENT_SECRETS_DIR, every
    *_API_KEY constant silently resolves to None, surfacing only as a
    confusing auth error deep inside a model call. This doesn't change
    that a missing .env is a normal, supported state (a fresh clone) --
    it just makes the cause visible immediately via a stderr warning.
    """
    monkeypatch.setenv("AGENT_SECRETS_DIR", str(tmp_path / "does-not-exist"))
    importlib.reload(config)
    try:
        captured = capsys.readouterr()
        assert "no .env found" in captured.err
    finally:
        # Restore the module to its normal, already-imported state for
        # every other test in the suite.
        monkeypatch.delenv("AGENT_SECRETS_DIR", raising=False)
        importlib.reload(config)
