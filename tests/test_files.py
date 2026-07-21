from agent_core.tools.files import read_file, write_file, list_files


def test_write_then_read_roundtrip(tmp_path):
    sandbox = str(tmp_path)
    out = write_file.invoke({"sandbox": sandbox, "filename": "note.txt", "content": "hello"})
    assert "Written" in out
    back = read_file.invoke({"sandbox": sandbox, "filename": "note.txt"})
    assert back == "hello"


def test_read_missing_file_is_graceful(tmp_path):
    result = read_file.invoke({"sandbox": str(tmp_path), "filename": "nope.txt"})
    assert "not found" in result.lower()


def test_write_creates_nested_dirs(tmp_path):
    sandbox = str(tmp_path)
    write_file.invoke({"sandbox": sandbox, "filename": "a/b/c.txt", "content": "deep"})
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


def test_list_files_sorted(tmp_path):
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "a.txt").write_text("")
    result = list_files.invoke({"sandbox": str(tmp_path)})
    assert result == "a.txt\nb.txt"


def test_list_empty_sandbox(tmp_path):
    assert "No files" in list_files.invoke({"sandbox": str(tmp_path)})


def test_file_tool_blocks_sandbox_escape(tmp_path):
    import pytest
    sandbox = str(tmp_path / "box")
    (tmp_path / "box").mkdir()
    (tmp_path / "secret.txt").write_text("classified")
    with pytest.raises(ValueError):
        read_file.invoke({"sandbox": sandbox, "filename": "../secret.txt"})
