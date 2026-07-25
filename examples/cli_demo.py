"""
Thin CLI entrypoint - the pattern every real entrypoint follows.

Defines an AgentSpec, hands it to build_agent(), and runs a REPL loop.
This is the "Discord Bot" / "CLI Tool" box from the architecture diagram
in README.md, made concrete: nothing here is framework code, it's just
wiring one spec to stdin/stdout.

Run it:
    python examples/cli_demo.py

Watch it live in the 2D visualizer (see visualizer/README.md):
    1. Start this script - agent_core opens a WebSocket server on :8080
    2. Open visualizer/ in Godot 4 and run the main scene
    3. Ask the agent something - watch it walk to the tool node it calls
"""
import sys

from agent_core.spec import AgentSpec
from agent_core.agent import build_agent
from agent_core.tools.weather import get_weather
from agent_core.tools.digest import assemble_digest
from agent_core.tools.log import write_log, read_pending, add_pending, complete_pending
from agent_core.tools.files import read_file, write_file, list_files

SANDBOX = "./sandboxes/cli-demo"

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
)


def main() -> None:
    graph = build_agent(spec)
    config = {"configurable": {"thread_id": "cli"}}

    print(f"cli-demo ready. sandbox={SANDBOX}  (Ctrl+C or 'exit' to quit)\n")
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
