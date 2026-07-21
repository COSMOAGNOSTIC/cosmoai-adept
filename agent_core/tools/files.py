import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.security import safe_path


class ReadFileInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")
    filename: str = Field(description="Name of file to read, relative to sandbox")


class WriteFileInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")
    filename: str = Field(description="Name of file to write, relative to sandbox")
    content: str = Field(description="Content to write to the file")


class ListFilesInput(BaseModel):
    sandbox: str = Field(description="Agent sandbox directory path")


@tool(args_schema=ReadFileInput)
def read_file(sandbox: str, filename: str) -> str:
    """Read a file from the agent's sandbox. Cannot read outside the sandbox."""
    path = safe_path(sandbox, filename)
    if not os.path.exists(path):
        return f"File not found: {filename}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@tool(args_schema=WriteFileInput)
def write_file(sandbox: str, filename: str, content: str) -> str:
    """Write content to a file in the agent's sandbox. Cannot write outside the sandbox."""
    path = safe_path(sandbox, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written: {filename}"


@tool(args_schema=ListFilesInput)
def list_files(sandbox: str) -> str:
    """List all files in the agent's sandbox directory."""
    real = os.path.realpath(sandbox)
    if not os.path.exists(real):
        return f"Sandbox not found: {sandbox}"
    files = [
        f for f in os.listdir(real)
        if os.path.isfile(os.path.join(real, f))
    ]
    if not files:
        return "No files found."
    return "\n".join(sorted(files))
