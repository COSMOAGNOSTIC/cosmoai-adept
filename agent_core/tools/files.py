import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.security import safe_path


class ReadFileInput(BaseModel):
    filename: str = Field(description="Name of file to read, relative to the agent's sandbox")


class WriteFileInput(BaseModel):
    filename: str = Field(description="Name of file to write, relative to the agent's sandbox")
    content: str = Field(description="Content to write to the file")


class ListFilesInput(BaseModel):
    pass


def make_file_tools(sandbox: str):
    """
    Build read_file/write_file/list_files bound to a single sandbox root.

    `sandbox` is closed over here - it is never a model-supplied tool
    argument. Earlier versions of this module took `sandbox` as a tool
    input, which meant the model chose the sandbox root and `safe_path()`
    only guarded escape *within* whatever root it was handed - a model
    could pass `sandbox="/etc"` and read outside the intended box
    entirely. The sandbox root is now bound once, by whoever constructs
    the AgentSpec, before the model ever sees a tool - matching
    ARCHITECTURE.md's "security lives in the tool layer, not the prompt
    layer" principle for real, not just in the argument names. See the
    Decision Log for the ADR.
    """

    @tool(args_schema=ReadFileInput)
    def read_file(filename: str) -> str:
        """Read a file from the agent's sandbox. Cannot read outside the sandbox."""
        path = safe_path(sandbox, filename)
        if not os.path.exists(path):
            return f"File not found: {filename}"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @tool(args_schema=WriteFileInput)
    def write_file(filename: str, content: str) -> str:
        """Write content to a file in the agent's sandbox. Cannot write outside the sandbox."""
        path = safe_path(sandbox, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written: {filename}"

    @tool(args_schema=ListFilesInput)
    def list_files() -> str:
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

    return read_file, write_file, list_files
