# PASSDOWN

> Read this first when picking the project back up. It answers: what's done, what's next, and what was decided but not yet built — so you never have to re-derive context from commit history.
> Update this at the end of every working session, even a short one. If MIGRATION.md is the map, this is "you are here."

---

## 2026-07-25 (latest) — HITL approval gate + local LLM backend

**Where things stood coming in:** an externally-pasted PASSDOWN document (from a different session) proposed a HITL "Approval Switch" and a local-LLM-backend integration as open TODOs. Cross-checking it against the actual repo showed most of that document's other items were already done (LICENSE, events.py, visualizer, Mermaid diagram) — but these two were genuinely new scope, and non-trivial enough (direct-attention features, not background plumbing) to build and document properly rather than skip.

**What got built:**
- `agent_core/approvals.py` — `default_cli_approval_hook`, a blocking terminal y/N prompt, used when a spec supplies no hook of its own.
- `spec.py` — `AgentSpec.approval_required: set[str]` (tool names that must pause) and `AgentSpec.approval_hook` (swappable decision function).
- `agent.py` — `execute_tools` now checks `approval_required` before invoking a gated tool; emits `awaiting_approval` then `approval_decided` over the existing event stream; a denial returns a `ToolMessage` explaining the refusal rather than raising, consistent with the existing tool-error-recovery principle.
- `spec.py` / `config.py` / `agent.py` — `AgentSpec.backend` (`"anthropic"` default, `"local"`), `local_base_url`, `LOCAL_LLM_BASE_URL` env default `http://localhost:1234/v1`; `_build_model()` is the single branch point between `ChatAnthropic` and `ChatOpenAI` (via new `langchain-openai` dependency) — everything else (graph, tools, memory, events) is identical either way.
- `examples/cli_demo.py` — `--local` flag to run against a local server instead of the API, `write_file` gated behind approval as the worked example.
- Visualizer: added an "APPROVAL" station (orange, `Main.gd`'s `STATION_LAYOUT`/`STATION_COLOR`), new `match` branches for `awaiting_approval` (walk to station, show which tool is waiting) and `approval_decided` (show approved/denied). `demo_broadcaster.py`'s script extended with a full approval sequence. Re-recorded the demo GIF and screenshot-verified the orange node renders correctly alongside the other five.
- Tests: `tests/test_approvals.py` (new, 4 cases), `tests/test_agent.py` extended with approved/denied/ungated tool-call cases and backend-selection cases (`FakeApprovalModel`, `test_default_backend_uses_chat_anthropic`, `test_local_backend_uses_chat_openai_with_base_url`, `test_local_backend_falls_back_to_config_base_url`). 42/42 passing.
- Docs: README (hero framing already covered the visualizer; added dedicated "Human-in-the-Loop Approval" and "Local LLM Backend" sections, two new Core Architectural Principles bullets, Mermaid diagram extended with an Approval node and a Models subgraph), `visualizer/README.md` (event table rows for the two new events), ARCHITECTURE.md (Design Principle 6, Components table, new sections 7–8, ADR-007/008, a new Known Debt item for non-CLI approval hooks), MIGRATION.md (Phase 6, Phase 5 backfilled for the skin work, Phase 7 renumbered from the old Phase 5).

**Decided but not built:**
- No non-CLI approval hook reference implementation yet (a Discord reaction confirm, a Slack button) — `default_cli_approval_hook` is explicitly documented as wrong for unattended entrypoints. Tracked as debt in ARCHITECTURE.md and as a Phase 7 item.
- Whether `cosmo-core` (the private production sibling) should also get these two features was raised but not confirmed — this work was scoped to `cosmoai-adept` only this session.

**Open questions for next session:**
- Port HITL approval + local backend to `cosmo-core`? Needs an explicit yes from the project owner before touching the production repo.
- Is a Discord-reaction approval hook worth building next, given the Discord bot is the actual unattended deployment target this gate would matter most for?

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
