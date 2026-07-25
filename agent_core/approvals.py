"""
Human-in-the-loop approval for high-risk tool calls.

A tool is high-risk by *name*, declared on the AgentSpec
(`approval_required: set[str]`) - not by inspecting arguments, so the
gate is mechanical and can't be argued around by clever prompting.

The hook is pluggable: an AgentSpec can supply its own
`approval_hook(tool_name, args) -> bool` (e.g. a Discord reaction
prompt, a Slack approval button). If none is supplied, tools in
`approval_required` fall back to `default_cli_approval_hook`, a
blocking terminal y/N prompt - fine for `examples/cli_demo.py`, wrong
for anything running unattended.
"""
from typing import Any, Callable

ApprovalHook = Callable[[str, dict[str, Any]], bool]


def default_cli_approval_hook(tool_name: str, args: dict[str, Any]) -> bool:
    """Blocking terminal prompt. Only appropriate for interactive entrypoints."""
    print(f"\n[APPROVAL REQUIRED] {tool_name}({args})")
    response = input("Approve this tool call? [y/N]: ").strip().lower()
    return response in ("y", "yes")
