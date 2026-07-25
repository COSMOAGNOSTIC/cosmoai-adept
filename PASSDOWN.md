# PASSDOWN

> Read this first when picking the project back up. It answers: what's done, what's next, and what was decided but not yet built — so you never have to re-derive context from commit history.
> Update this at the end of every working session, even a short one. If MIGRATION.md is the map, this is "you are here."

---

## 2026-07-25 (later same day) — Visualizer skin: Circuit

**Where things stood coming in:** first visualizer pass used flat `ColorRect` placeholders and a fixed 1.8s speech bubble regardless of text length — too fast to read, especially in a recorded demo.

**What got built:**
- Chose "Circuit" skin after reviewing static mockups against a rejected alternative pair (sci-fi vs. RPG office/cottage look) — went sci-fi/telemetry for this public repo specifically, since it reads as systems observability rather than a game.
- `visualizer/assets/gen_assets.py` — generates `bg_circuit.png` (dark grid + vignette), `node_glow.png` (radial glow, tinted per station via `Sprite2D.modulate`), `scanlines.png` (CRT overlay). Committed output, not generated at runtime.
- `Main.gd` rewritten: glowing station nodes, right-angle circuit-trace lines from agent to whichever station it's headed to, diamond-shaped pulsing agent core, HUD-style bordered speech bubble.
- Speech bubble timing fixed: `clamp(text.length() / 12, 3.0, 7.0)` seconds instead of a flat 1.8s — floor keeps even "done" legible, cap keeps a long response from stalling the scene.
- `demo_broadcaster.py` step interval bumped 1.4s → 3.2s to match the new floor, so the recorded GIF is actually readable.
- Re-recorded demo GIF, re-embedded in README.md.

**Decided but not built:**
- Kenney.nl CC0 tileset swap (originally planned) is superseded by the Circuit direction for this repo — no longer the plan here. `cosmo-core`'s sibling visualizer went the pixel-art office route instead; see that repo's PASSDOWN.md.

**Open questions for next session:**
- None outstanding on the visualizer itself. Phase 5 items (event schema versioning, eval harness) are still open, unrelated to this skin work.

---

## 2026-07-25 — Observability, digest tool, live visualizer

**Where things stood coming in:** `agent_core` had a full tool library (files, log, search, weather, tts) and a full test suite, but no real entrypoint — the README's Quick Start was a snippet, not a runnable script — and no digest tool despite the README describing one.

**What got built:**
- `agent_core/events.py` — lazy WebSocket broadcaster (`ws://localhost:8080`), no-op with no listener, wired into `agent.py`'s `call_model` / `execute_tools` at four emit points.
- `agent_core/tools/digest.py` — the digest pattern the README already promised: sandbox state (pending items, recent activity) plus live search, one report.
- `examples/cli_demo.py` — real thin entrypoint, REPL loop, all tools wired.
- `visualizer/` — Godot 4 project. Procedural scene (no external asset dependency yet), `Main.gd` connects as a WebSocket client, animates the agent walking between five stations (Model, Weather, Digest Desk, Log, Files) with speech bubbles, reconnects automatically if the agent process restarts.
- `visualizer/demo_broadcaster.py` — replays a scripted event sequence so the visualizer can be demoed/recorded without an API key.
- Recorded a demo GIF (Xvfb + Godot + ffmpeg), embedded at the top of README.md.
- 32/32 tests passing (`test_events.py`, `test_digest.py` new).
- README reframed: "real-time spatial visualizer and telemetry dashboard for multi-agent systems," architecture diagram extended to show the events → visualizer path.
- ARCHITECTURE.md and MIGRATION.md written for this repo specifically (previously only existed for the private `cosmo-core` sibling project, never for this public one) — see Decision Log in ARCHITECTURE.md, Phase 3/4 in MIGRATION.md.

**Decided but not built (Phase 5 in MIGRATION.md):**
- Event schema has no version field. Fine with one consumer (the visualizer); needs one before a second consumer is built against it.
- Visualizer graphics are procedural `ColorRect` placeholders. Plan is a CC0 top-down tileset from Kenney.nl — swap point is documented in `visualizer/README.md`, logic doesn't change.
- No eval harness yet — scripted scenarios scoring agent output quality, mentioned as debt in ARCHITECTURE.md.

**Open questions for next session:**
- Does the digest tool need a second `topic` example beyond the default, to show it's genuinely reusable and not just a copy of the news block?
- Worth adding a `schema_version` field to events now, before Phase 5, since it's a one-line change and much cheaper before a second consumer exists?

**Culture note — apply this going forward, on every project:** every repo gets `MIGRATION.md` (phased build history, DoD per phase), `ARCHITECTURE.md` (present-tense living doc, decision log), and `PASSDOWN.md` (this file — session log, updated every sitting). The point is that "done" has a written definition and picking the project back up after months away doesn't require reconstructing context from git log.
