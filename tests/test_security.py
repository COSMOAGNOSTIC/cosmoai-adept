import os
import pytest
from agent_core.security import safe_open, safe_path


def _symlink_or_skip(link_path, target):
    """
    Creating a symlink on Windows requires SeCreateSymbolicLinkPrivilege
    (admin, or Developer Mode enabled) - a non-elevated shell raises
    OSError [WinError 1314]. That's an environment limitation, not a
    safe_open() bug, so these tests skip rather than fail when the
    environment can't set up the scenario they're testing.
    """
    try:
        link_path.symlink_to(target)
    except OSError as e:
        pytest.skip(f"cannot create symlinks in this environment: {e}")


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


# --- safe_open(): TOCTOU regression tests ---------------------------------
#
# safe_path() alone validates a path *string*; a plain open(that_string)
# later has a window where something could swap a symlink into place
# in between. These tests exercise safe_open()'s two independent closes
# of that window: O_NOFOLLOW on the syscall itself (final component),
# and a post-open /proc/self/fd re-check (intermediate components).


def test_safe_open_write_then_read_roundtrip(tmp_path):
    base = str(tmp_path)
    with safe_open(base, "note.txt", "w") as f:
        f.write("hello")
    with safe_open(base, "note.txt", "r") as f:
        assert f.read() == "hello"


def test_safe_open_append(tmp_path):
    base = str(tmp_path)
    with safe_open(base, "log.txt", "a") as f:
        f.write("a\n")
    with safe_open(base, "log.txt", "a") as f:
        f.write("b\n")
    with safe_open(base, "log.txt", "r") as f:
        assert f.read() == "a\nb\n"


def test_safe_open_binary_mode(tmp_path):
    base = str(tmp_path)
    with safe_open(base, "audio.bin", "wb") as f:
        f.write(b"\x00\x01")
    with safe_open(base, "audio.bin", "rb") as f:
        assert f.read() == b"\x00\x01"


def test_safe_open_read_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        safe_open(str(tmp_path), "nope.txt", "r")


def test_safe_open_rejects_symlink_at_final_component_for_read(tmp_path):
    """
    The exact race this exists to close: the target *file* gets swapped
    for a symlink pointing outside the sandbox. A plain
    open(safe_path(...)) would silently follow it; safe_open() must not.
    """
    base = tmp_path / "sandbox"
    base.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("classified")
    _symlink_or_skip(base / "note.txt", outside)

    with pytest.raises(ValueError):
        safe_open(str(base), "note.txt", "r")


def test_safe_open_rejects_symlink_at_final_component_for_write(tmp_path):
    base = tmp_path / "sandbox"
    base.mkdir()
    outside = tmp_path / "target.txt"
    _symlink_or_skip(base / "out.txt", outside)

    with pytest.raises(ValueError):
        safe_open(str(base), "out.txt", "w")
    assert not outside.exists()


def test_safe_open_rejects_symlinked_intermediate_directory(tmp_path):
    """
    O_NOFOLLOW alone only guards the final path component - this proves
    the post-open /proc/self/fd re-validation catches a symlink swapped
    into a *directory* component instead of the file itself, which
    O_NOFOLLOW would not catch on its own.
    """
    base = tmp_path / "sandbox"
    base.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("classified")
    _symlink_or_skip(base / "sub", outside_dir)

    with pytest.raises(ValueError):
        safe_open(str(base), os.path.join("sub", "secret.txt"), "r")


def test_safe_open_still_enforces_dotdot_traversal(tmp_path):
    base = str(tmp_path)
    with pytest.raises(ValueError):
        safe_open(base, os.path.join("..", "escape.txt"), "w")


def test_safe_open_rejects_unsupported_mode(tmp_path):
    with pytest.raises(ValueError):
        safe_open(str(tmp_path), "x.txt", "x")


def test_safe_open_closes_the_actual_toctou_race(tmp_path, monkeypatch):
    """
    The tests above place the symlink *before* calling safe_open(), which
    safe_path()'s own realpath-based check already caught even in the old
    safe_path()-then-plain-open() code - they're sanity checks, not proof
    the race is closed.

    This one simulates the literal race the fix exists for: the path
    passes safe_path()'s check while it's still an ordinary target, and
    only *after* that check completes - simulating something else
    swapping a symlink into place in the gap - does the symlink appear,
    before the subsequent open() syscall runs. Old code (plain
    open(safe_path(...))) would follow that symlink straight through,
    since safe_path() had already returned by the time the swap
    happened. safe_open()'s O_NOFOLLOW makes the open() syscall itself
    refuse, regardless of what happened in the gap.
    """
    import agent_core.security as security_module

    base = tmp_path / "sandbox"
    base.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("classified")

    real_safe_path = security_module.safe_path

    def racing_safe_path(b, filename):
        result = real_safe_path(b, filename)  # passes - nothing symlinked yet
        _symlink_or_skip(base / "note.txt", outside)  # attacker wins the race here
        return result

    monkeypatch.setattr(security_module, "safe_path", racing_safe_path)

    with pytest.raises(ValueError):
        security_module.safe_open(str(base), "note.txt", "r")
