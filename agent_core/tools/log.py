import os
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.security import safe_path


class LogInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")
    entry: str = Field(description="Log entry text to append")


class PendingInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")


class AddPendingInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")
    item: str = Field(description="Pending item to add")


class CompletePendingInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")
    item_number: int = Field(description="1-based line number of the item to mark complete and remove")


@tool(args_schema=LogInput)
def write_log(sandbox: str, entry: str) -> str:
    """Append a timestamped entry to the agent activity log."""
    path = safe_path(sandbox, "activity_log.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {entry}\n")
    return f"Logged: {entry}"


@tool(args_schema=PendingInput)
def read_pending(sandbox: str) -> str:
    """Read all pending items."""
    path = safe_path(sandbox, "pending.txt")
    if not os.path.exists(path):
        return "No pending items."
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return content if content else "No pending items."


@tool(args_schema=AddPendingInput)
def add_pending(sandbox: str, item: str) -> str:
    """Add a new pending item."""
    path = safe_path(sandbox, "pending.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{item}\n")
    return f"Added: {item}"


@tool(args_schema=CompletePendingInput)
def complete_pending(sandbox: str, item_number: int) -> str:
    """
    Remove a single completed pending item by its 1-based line number.
    Only removes the specified item - all others are preserved.
    """
    path = safe_path(sandbox, "pending.txt")
    if not os.path.exists(path):
        return "No pending items."
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f.readlines()]
    if item_number < 1 or item_number > len(lines):
        return f"Invalid item number: {item_number}. There are {len(lines)} items."
    removed = lines.pop(item_number - 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return f"Completed: {removed}"
