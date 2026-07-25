from agent_core.approvals import default_cli_approval_hook


def test_default_hook_approves_on_y(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert default_cli_approval_hook("some_tool", {"arg": 1}) is True


def test_default_hook_approves_on_yes_case_insensitive(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "YES")
    assert default_cli_approval_hook("some_tool", {}) is True


def test_default_hook_denies_on_empty_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert default_cli_approval_hook("some_tool", {}) is False


def test_default_hook_denies_on_explicit_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert default_cli_approval_hook("some_tool", {}) is False
