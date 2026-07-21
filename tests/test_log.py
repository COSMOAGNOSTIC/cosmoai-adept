from agent_core.tools.log import write_log, read_pending, add_pending, complete_pending


def test_write_log_appends_timestamped(tmp_path):
    sandbox = str(tmp_path)
    write_log.invoke({"sandbox": sandbox, "entry": "did a thing"})
    contents = (tmp_path / "activity_log.txt").read_text()
    assert "did a thing" in contents
    assert contents.startswith("[")


def test_pending_lifecycle(tmp_path):
    sandbox = str(tmp_path)
    assert "No pending" in read_pending.invoke({"sandbox": sandbox})
    add_pending.invoke({"sandbox": sandbox, "item": "first"})
    add_pending.invoke({"sandbox": sandbox, "item": "second"})
    assert "first" in read_pending.invoke({"sandbox": sandbox})

    done = complete_pending.invoke({"sandbox": sandbox, "item_number": 1})
    assert "first" in done
    remaining = read_pending.invoke({"sandbox": sandbox})
    assert "second" in remaining
    assert "first" not in remaining


def test_complete_invalid_number(tmp_path):
    sandbox = str(tmp_path)
    add_pending.invoke({"sandbox": sandbox, "item": "only"})
    result = complete_pending.invoke({"sandbox": sandbox, "item_number": 5})
    assert "Invalid" in result


def test_complete_last_item_empties_file(tmp_path):
    sandbox = str(tmp_path)
    add_pending.invoke({"sandbox": sandbox, "item": "only"})
    complete_pending.invoke({"sandbox": sandbox, "item_number": 1})
    assert "No pending" in read_pending.invoke({"sandbox": sandbox})
