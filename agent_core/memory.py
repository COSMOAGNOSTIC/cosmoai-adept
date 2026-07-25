import os
from langgraph.checkpoint.sqlite import SqliteSaver


def make_checkpointer(memory_dir: str, agent_name: str) -> SqliteSaver:
    """
    Create a SqliteSaver checkpointer for the given agent, in `memory_dir`.

    `memory_dir` must never be a directory the agent's own tools can reach.
    An independent code review found `build_agent()` used to call this with
    the agent's *sandbox* path -- the same directory `safe_path()`-bound
    file tools are rooted at -- so a model could read other conversations'
    history (a real information leak between threads/users of the same
    agent) or corrupt its own checkpoint DB using its own ordinary file
    tools. "Never in secrets, never in cloud sync" was true and remains
    true; "never reachable by the model itself" was not, and is the actual
    property this function needs. Callers should use
    `agent_core.config.memory_path()`, which defaults to a directory
    that is never any agent's sandbox root.

    One DB per agent, one thread per conversation (thread_id = channel/session id).
    """
    # Fresh clones don't have a memory directory yet - without this, sqlite3
    # raises OperationalError before an agent has ever run once (this broke
    # the README Quick Start and cli_demo.py on a clean checkout; see
    # PASSDOWN.md).
    os.makedirs(memory_dir, exist_ok=True)
    db_path = os.path.join(memory_dir, f"{agent_name}_memory.db")
    conn = __import__("sqlite3").connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)
