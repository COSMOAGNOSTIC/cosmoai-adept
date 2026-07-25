import os
from langgraph.checkpoint.sqlite import SqliteSaver


def make_checkpointer(sandbox: str, agent_name: str) -> SqliteSaver:
    """
    Create a SqliteSaver checkpointer for the given agent.
    DB lives in the agent's sandbox - never in secrets, never in cloud sync.
    One DB per agent, one thread per conversation (thread_id = channel/session id).
    """
    # Fresh clones don't have a sandbox directory yet - without this, sqlite3
    # raises OperationalError before an agent has ever run once (this broke
    # the README Quick Start and cli_demo.py on a clean checkout; see
    # PASSDOWN.md).
    os.makedirs(sandbox, exist_ok=True)
    db_path = os.path.join(sandbox, f"{agent_name}_memory.db")
    conn = __import__("sqlite3").connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)
