import pytest

from agent_core.tools.files import make_file_tools


def test_write_then_read_roundtrip(tmp_path):
    sandbox = str(tmp_path)
    read_file, write_file, list_files = make_file_tools(sandbox)
    out = write_file.invoke({"filename": "note.txt", "content": "hello"})
    assert "Written" in out
    back = read_file.invoke({"filename": "note.txt"})
    assert back == "hello"


def test_read_missing_file_is_graceful(tmp_path):
    read_file, write_file, list_files = make_file_tools(str(tmp_path))
    result = read_file.invoke({"filename": "nope.txt"})
    assert "not found" in result.lower()


def test_write_creates_nested_dirs(tmp_path):
    sandbox = str(tmp_path)
    read_file, write_file, list_files = make_file_tools(sandbox)
    write_file.invoke({"filename": "a/b/c.txt", "content": "deep"})
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


def test_list_files_sorted(tmp_path):
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "a.txt").write_text("")
    read_file, write_file, list_files = make_file_tools(str(tmp_path))
    result = list_files.invoke({})
    assert result == "a.txt\nb.txt"


def test_list_empty_sandbox(tmp_path):
    read_file, write_file, list_files = make_file_tools(str(tmp_path))
    assert "No files" in list_files.invoke({})


def test_file_tool_blocks_sandbox_escape(tmp_path):
    sandbox = str(tmp_path / "box")
    (tmp_path / "box").mkdir()
    (tmp_path / "secret.txt").write_text("classified")
    read_file, write_file, list_files = make_file_tools(sandbox)
    with pytest.raises(ValueError):
        read_file.invoke({"filename": "../secret.txt"})


def test_file_tools_do_not_accept_a_sandbox_argument(tmp_path):
    """
    The sandbox root is bound at construction time via make_file_tools(),
    never accepted from the model - a tool that still took `sandbox` as an
    argument would let a model choose its own root (e.g. "/etc") and read
    or write outside the intended sandbox entirely. This is the regression
    test for that fix.
    """
    read_file, write_file, list_files = make_file_tools(str(tmp_path))
    for t in (read_file, write_file, list_files):
        field_names = set(t.args_schema.model_fields.keys())
        assert "sandbox" not in field_names


def test_file_tool_blocks_symlink_swapped_into_sandbox(tmp_path):
    """
    read_file/write_file now go through agent_core.security.safe_open()
    instead of safe_path()-then-plain-open(). A symlink already sitting
    at the target path is caught here too (this is a sanity check, not
    proof of the fix by itself - safe_path()'s own realpath resolution
    already caught a pre-existing symlink even before this session's
    fix). The actual TOCTOU-race regression test - the symlink appearing
    *after* the safe_path() check has already passed, which the old
    plain-open() code would have silently followed - lives in
    tests/test_security.py::test_safe_open_closes_the_actual_toctou_race.
    """
    sandbox = tmp_path / "box"
    sandbox.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("classified")
    try:
        (sandbox / "note.txt").symlink_to(secret)
    except OSError as e:
        pytest.skip(f"cannot create symlinks in this environment: {e}")

    read_file, write_file, list_files = make_file_tools(str(sandbox))
    with pytest.raises(ValueError):
        read_file.invoke({"filename": "note.txt"})
    with pytest.raises(ValueError):
        write_file.invoke({"filename": "note.txt", "content": "overwritten"})
    assert secret.read_text() == "classified"


def test_two_sandboxes_are_isolated(tmp_path):
    """Two agents built with different sandboxes never see each other's files."""
    box_a = tmp_path / "a"
    box_b = tmp_path / "b"
    box_a.mkdir()
    box_b.mkdir()
    read_a, write_a, _ = make_file_tools(str(box_a))
    read_b, write_b, _ = make_file_tools(str(box_b))

    write_a.invoke({"filename": "secret.txt", "content": "a's secret"})
    result = read_b.invoke({"filename": "secret.txt"})
    assert "not found" in result.lower()
