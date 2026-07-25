"""
Thin CLI entrypoint - the pattern every real entrypoint follows.

Defines an AgentSpec, hands it to build_agent(), and runs a REPL loop.
This is the "Discord Bot" / "CLI Tool" box from the architecture diagram
in README.md, made concrete: nothing here is framework code, it's just
wiring one spec to stdin/stdout.

Run it:
    python examples/cli_demo.py

Run it against a local, GPU-offloaded model instead of the Claude API
(e.g. LM Studio serving Qwen2.5-Coder or Gemma on localhost:1234) - zero
API cost, zero network egress:
    python examples/cli_demo.py --local

Watch it live in the 2D visualizer (see visualizer/README.md):
    1. Start this script - agent_core opens a WebSocket server on :8080
    2. Open visualizer/ in Godot 4 and run the main scene
    3. Ask the agent something - watch it walk to the tool node it calls
    4. Ask it to write a file - it'll pause at the Approval Switch node
       and wait for a y/N in this terminal before the write happens
"""
import sys

from agent_core.spec import AgentSpec
from agent_core.agent import build_agent
from agent_core.tools.weather import get_weather
from agent_core.tools.digest import assemble_digest
from agent_core.tools.log import write_log, read_pending, add_pending, complete_pending
from agent_core.tools.files import read_file, write_file, list_files

SANDBOX = "./sandboxes/cli-demo"
USE_LOCAL_BACKEND = "--local" in sys.argv

spec = AgentSpec(
    name="cli-demo",
    system_prompt=(
        "You are a terse, helpful assistant with tools for weather, a "
        "sandboxed scratchpad, activity logging, and a digest that pulls "
        f"your pending items plus live search results into one report. "
        f"Your sandbox directory is '{SANDBOX}' - pass it as the `sandbox` "
        "argument to any tool that requires one. Prefer using tools over "
        "guessing."
    ),
    tools=[
        get_weather,
        assemble_digest,
        write_log,
        read_pending,
        add_pending,
        complete_pending,
        read_file,
        write_file,
        list_files,
    ],
    sandbox=SANDBOX,
    # write_file mutates the sandbox, so it pauses for a human y/N before
    # running - the default_cli_approval_hook prompt in agent_core/approvals.py.
    approval_required={"write_file"},
    backend="local" if USE_LOCAL_BACKEND else "anthropic",
    model="qwen2.5-coder-14b-instruct" if USE_LOCAL_BACKEND else "claude-sonnet-4-6",
)


def main() -> None:
    graph = build_agent(spec)
    config = {"configurable": {"thread_id": "cli"}}

    print(
        f"cli-demo ready. backend={spec.backend} model={spec.model} "
        f"sandbox={SANDBOX}  (Ctrl+C or 'exit' to quit)\n"
    )
    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        result = graph.invoke(
            {"messages": [("user", user_input)]},
            config=config,
        )
        print(f"agent> {result['messages'][-1].content}\n")


if __name__ == "__main__":
    sys.exit(main() or 0)
