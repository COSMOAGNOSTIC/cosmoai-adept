from agent_core.text import extract_text, chunk_for_discord


def test_extract_plain_string():
    assert extract_text("hello") == "hello"


def test_extract_content_blocks():
    blocks = [{"type": "text", "text": "part one "}, {"type": "text", "text": "part two"}]
    assert extract_text(blocks) == "part one part two"


def test_extract_mixed_list_of_strings_and_blocks():
    blocks = ["a", {"type": "text", "text": "b"}, "c"]
    assert extract_text(blocks) == "abc"


def test_extract_ignores_non_text_blocks():
    blocks = [{"type": "image", "url": "x"}, {"type": "text", "text": "kept"}]
    assert extract_text(blocks) == "kept"


def test_extract_falls_back_to_str():
    assert extract_text(42) == "42"


def test_chunk_short_text_single_chunk():
    assert chunk_for_discord("short") == ["short"]


def test_chunk_respects_limit():
    text = "\n".join("line %d" % i for i in range(1000))
    chunks = chunk_for_discord(text, limit=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert all(c != "" for c in chunks)


def test_chunk_hard_splits_when_no_newline():
    text = "x" * 500
    chunks = chunk_for_discord(text, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == text
