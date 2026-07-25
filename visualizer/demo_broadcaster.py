"""
Standalone driver that replays a realistic tool-call sequence over the
agent_core WebSocket broadcaster - no API keys required. Useful for:

- Trying out the visualizer without wiring up a real agent
- Recording a demo GIF/video
- Smoke-testing the visualizer's event handling

Run this, then open visualizer/ in Godot 4 and run the main scene
(or run it headless - see README.md in this folder).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_core import events  # noqa: E402

SCRIPT = [
    ("model_start", {"agent": "cli-demo"}),
    ("model_end", {"agent": "cli-demo", "tool_calls": ["get_weather"], "text": ""}),
    ("tool_start", {"agent": "cli-demo", "tool": "get_weather"}),
    ("tool_end", {"agent": "cli-demo", "tool": "get_weather", "ok": True}),
    ("model_start", {"agent": "cli-demo"}),
    ("model_end", {"agent": "cli-demo", "tool_calls": ["assemble_digest"], "text": ""}),
    ("tool_start", {"agent": "cli-demo", "tool": "assemble_digest"}),
    ("tool_end", {"agent": "cli-demo", "tool": "assemble_digest", "ok": True}),
    ("model_start", {"agent": "cli-demo"}),
    ("model_end", {"agent": "cli-demo", "tool_calls": ["write_log"], "text": ""}),
    ("tool_start", {"agent": "cli-demo", "tool": "write_log"}),
    ("tool_end", {"agent": "cli-demo", "tool": "write_log", "ok": True}),
    ("model_start", {"agent": "cli-demo"}),
    (
        "model_end",
        {
            "agent": "cli-demo",
            "tool_calls": [],
            "text": "It's 61F and clear in Bremerton, WA. Logged and ready for the next one.",
        },
    ),
]


def main() -> None:
    broadcaster = events.get_broadcaster()
    broadcaster.start()
    print("Waiting for the visualizer to connect on ws://localhost:8080 ...")
    time.sleep(3)
    print("Replaying demo sequence.")
    for event_type, payload in SCRIPT:
        broadcaster.emit(event_type, **payload)
        time.sleep(1.4)
    print("Done.")


if __name__ == "__main__":
    main()
