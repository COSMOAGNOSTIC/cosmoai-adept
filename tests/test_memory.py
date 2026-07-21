import os
from agent_core.memory import make_checkpointer


def test_checkpointer_creates_db_in_sandbox(tmp_path):
    saver = make_checkpointer(str(tmp_path), "agent_a")
    assert saver is not None
    assert os.path.exists(str(tmp_path / "agent_a_memory.db"))


def test_each_agent_gets_own_db(tmp_path):
    make_checkpointer(str(tmp_path), "agent_a")
    make_checkpointer(str(tmp_path), "agent_b")
    assert os.path.exists(str(tmp_path / "agent_a_memory.db"))
    assert os.path.exists(str(tmp_path / "agent_b_memory.db"))
