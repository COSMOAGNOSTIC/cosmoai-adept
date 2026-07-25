# Live 2D Spatial Visualizer

A small Godot 4 project that renders `agent_core` activity as a top-down
scene: an agent sprite walks to the station for whichever tool it's
calling and pops a speech bubble with what it's doing.

## Why this exists

Log lines are accurate but slow to read. A 2D spatial view of "agent is
at the Weather station" is legible in under a second, and doubles as a
telemetry dashboard for a real multi-agent deployment — the same event
stream that drives this scene is what you'd feed into any other
front end (a web dashboard, Grafana, a Slack bot).

## Running it

1. Install [Godot 4.3+](https://godotengine.org/download).
2. Open this folder (`visualizer/`) as a project in the Godot editor, or run headless:
   ```
   godot --path visualizer/
   ```
3. Start anything that calls `agent_core.events.emit(...)` — either a real agent
   (`python examples/cli_demo.py`) or the scripted stand-in that needs no API key:
   ```
   python visualizer/demo_broadcaster.py
   ```
4. The visualizer connects to `ws://localhost:8080` automatically (with
   reconnect-on-drop) and starts animating as events arrive.

## How it works

`agent_core/events.py` starts a WebSocket server lazily, the first time
anything calls `emit()`. It's a pure broadcaster — no listener, no
effect. `Main.gd` connects as a client using Godot 4's built-in
`WebSocketPeer`, parses each JSON event, and:

| Event | Visual |
|---|---|
| `model_start` | agent walks to the "Model" station, shows "thinking..." |
| `model_end` (no tool calls) | speech bubble shows the response preview |
| `tool_start` | agent walks to the station mapped from the tool name |
| `tool_end` | speech bubble shows "done" or "error" |

The tool → station mapping lives in `TOOL_STATION` at the top of
`Main.gd` — add an entry there for any new tool.

## Assets

Everything here is drawn procedurally (`ColorRect` boxes, no textures)
so the project runs with zero external dependencies. For a polished
look, drop in a CC0 top-down tileset — [Kenney.nl](https://kenney.nl/assets)
has several — and swap the `ColorRect` nodes in `_build_stations()` /
`_build_agent()` in `Main.gd` for `Sprite2D` / `AnimatedSprite2D` nodes.
The event-handling logic doesn't change.

## Recording a demo GIF

```
Xvfb :99 -screen 0 960x540x24 &
export DISPLAY=:99
godot --path visualizer/ &
python visualizer/demo_broadcaster.py &
ffmpeg -f x11grab -video_size 960x540 -framerate 15 -i :99 -t 20 capture.mp4
ffmpeg -i capture.mp4 -vf "fps=12,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 demo.gif
```
