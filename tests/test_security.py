import os
import pytest
from agent_core.security import safe_path


def test_normal_file_stays_in_sandbox(tmp_path):
    base = str(tmp_path)
    result = safe_path(base, "activity_log.txt")
    assert result.startswith(os.path.realpath(base) + os.sep)
    assert result.endswith("activity_log.txt")


def test_nested_relative_path_allowed(tmp_path):
    base = str(tmp_path)
    result = safe_path(base, os.path.join("sub", "note.txt"))
    assert result.startswith(os.path.realpath(base) + os.sep)


def test_dotdot_traversal_rejected(tmp_path):
    base = str(tmp_path)
    with pytest.raises(ValueError):
        safe_path(base, os.path.join("..", "escape.txt"))


def test_deep_dotdot_traversal_rejected(tmp_path):
    base = str(tmp_path)
    with pytest.raises(ValueError):
        safe_path(base, os.path.join("..", "..", "..", "etc", "passwd"))


def test_absolute_path_rejected(tmp_path):
    base = str(tmp_path)
    outside = os.path.abspath(os.sep)
    with pytest.raises(ValueError):
        safe_path(base, outside)


def test_sibling_prefix_not_confused_for_sandbox(tmp_path):
    base = str(tmp_path / "sandbox")
    os.makedirs(base, exist_ok=True)
    os.makedirs(str(tmp_path / "sandbox_evil"), exist_ok=True)
    with pytest.raises(ValueError):
        safe_path(base, os.path.join("..", "sandbox_evil", "steal.txt"))
