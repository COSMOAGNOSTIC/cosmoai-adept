from agent_core.tools.log import make_log_tools


def test_write_log_appends_timestamped(tmp_path):
    sandbox = str(tmp_path)
    write_log, read_pending, add_pending, complete_pending = make_log_tools(sandbox)
    write_log.invoke({"entry": "did a thing"})
    contents = (tmp_path / "activity_log.txt").read_text()
    assert "did a thing" in contents
    assert contents.startswith("[")


def test_pending_lifecycle(tmp_path):
    sandbox = str(tmp_path)
    write_log, read_pending, add_pending, complete_pending = make_log_tools(sandbox)
    assert "No pending" in read_pending.invoke({})
    add_pending.invoke({"item": "first"})
    add_pending.invoke({"item": "second"})
    assert "first" in read_pending.invoke({})

    done = complete_pending.invoke({"item_number": 1})
    assert "first" in done
    remaining = read_pending.invoke({})
    assert "second" in remaining
    assert "first" not in remaining


def test_complete_invalid_number(tmp_path):
    sandbox = str(tmp_path)
    write_log, read_pending, add_pending, complete_pending = make_log_tools(sandbox)
    add_pending.invoke({"item": "only"})
    result = complete_pending.invoke({"item_number": 5})
    assert "Invalid" in result


def test_complete_last_item_empties_file(tmp_path):
    sandbox = str(tmp_path)
    write_log, read_pending, add_pending, complete_pending = make_log_tools(sandbox)
    add_pending.invoke({"item": "only"})
    complete_pending.invoke({"item_number": 1})
    assert "No pending" in read_pending.invoke({})


def test_log_tools_do_not_accept_a_sandbox_argument(tmp_path):
    tools = make_log_tools(str(tmp_path))
    for t in tools:
        field_names = set(t.args_schema.model_fields.keys())
        assert "sandbox" not in field_names
