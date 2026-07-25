# cosmoai-adept — Migration Plan

> **Goal:** From a single-purpose weather-bot script to a reusable `agent_core` library with a live observability layer, in phases, each one ending with the library in a working, tested state.
> **Companion doc:** ARCHITECTURE.md describes the destination; this file is the road.
> **Rule of the road:** one phase per sitting, each ends with `pytest -v` green. Never start a phase with the previous one's Definition of Done unmet.
> **Last updated:** 2026-07-25

---

## Phase 0 — Extract the core

- [x] `config.py` — all paths and keys from environment variables
- [x] `security.py` — `safe_path()` sandbox wall, with tests
- [x] `spec.py` — `AgentSpec` dataclass
- [x] `agent.py` — `build_agent()` ReAct graph factory
- [x] `memory.py` — `SqliteSaver` checkpointer factory
- [x] `text.py` — content normalizer, Discord chunker

**Definition of done:** ✅ Complete — core importable, `pip install -e .` clean.

---

## Phase 1 — Tool library

- [x] `tools/files.py`, `tools/log.py` — sandboxed I/O and activity tracking
- [x] `tools/search.py` — Tavily web search, dynamic year in query
- [x] `tools/weather.py` — OpenWeather, `timeout=10`, status checked before parse
- [x] `tools/tts.py` — single ElevenLabs implementation
- [x] Full pytest suite, one file per module

**Definition of done:** ✅ Complete — every tool has a matching test file.

---

## Phase 2 — CI and public release hygiene

- [x] GitHub Actions workflow, Python 3.11 and 3.12
- [x] MIT LICENSE
- [x] README with architecture diagram and Quick Start

**Definition of done:** ✅ Complete — badge green on `main`.

---

## Phase 3 — Observability and a second real feature

- [x] `events.py` — lazy WebSocket broadcaster, no-op with no listener
- [x] `agent.py` wired to emit `model_start` / `model_end` / `tool_start` / `tool_end`
- [x] `tools/digest.py` — scheduled digest pattern (sandbox state + live search into one report)
- [x] `examples/cli_demo.py` — real thin entrypoint, not just a README snippet
- [x] Tests for `events.py` and `tools/digest.py`

**Definition of done:** ✅ Complete — `pytest -v` green (32 tests), entrypoint runs end to end.

---

## Phase 4 — Live spatial visualizer

- [x] `visualizer/` — Godot 4 project, procedural scene (no external asset dependency)
- [x] `Main.gd` — `WebSocketPeer` client, reconnect-on-drop, tool → station mapping
- [x] `visualizer/demo_broadcaster.py` — scripted event replay, no API key required
- [x] Recorded demo GIF, embedded in README
- [x] `visualizer/README.md` — how it works, how to run it, how to swap in real sprites

**Definition of done:** ✅ Complete — demo GIF shows the agent walking between stations live.

---

## Phase 5 — Skin the visualizer, fix bubble timing

- [x] Rejected first-pass mockups (flat colors, clustered layout, fast bubbles) replaced after direct feedback
- [x] "Circuit" skin shipped for this repo — HUD/telemetry look, chosen over an RPG/office alternative
- [x] Universal bubble-timing fix: `clamp(text.length() / 12, 3.0, 7.0)` replacing a flat 1.8s
- [x] `demo_broadcaster.py` pacing slowed to match the new floor

**Definition of done:** ✅ Complete — demo GIF re-recorded and screenshot-verified with the new skin and timing.

---

## Phase 6 — Human-in-the-loop approval and local model backend

- [x] `agent_core/approvals.py` — `default_cli_approval_hook`, blocking CLI y/N prompt
- [x] `AgentSpec.approval_required`, `AgentSpec.approval_hook` — mechanical gate keyed on tool name, not prompt instruction
- [x] `agent.py`'s `execute_tools` pauses on a gated tool call, emits `awaiting_approval` / `approval_decided`, returns a `ToolMessage` on denial instead of raising
- [x] `AgentSpec.backend` (`"anthropic"` | `"local"`), `AgentSpec.local_base_url`, `config.LOCAL_LLM_BASE_URL` — swappable model client via `_build_model()`
- [x] `examples/cli_demo.py` — `--local` flag, `write_file` gated behind approval
- [x] Visualizer: `Main.gd` renders an "APPROVAL" station, handles `awaiting_approval` / `approval_decided`; `demo_broadcaster.py` script extended with an approval sequence; demo GIF re-recorded and screenshot-verified
- [x] `tests/test_approvals.py`, new cases in `tests/test_agent.py` — approved/denied/ungated tool calls, both backends
- [x] README, `visualizer/README.md`, ARCHITECTURE.md updated (sections 7–8, ADR-007/008, Design Principle 6)

**Definition of done:** ✅ Complete — `pytest -v` green (42 tests), visualizer shows the Approval node live, both backends covered by tests.

---

## Phase 7 — Lock it in

- [ ] Event schema versioning (`schema_version` field) before a second consumer is built against it
- [ ] Swap procedural visualizer graphics for a CC0 tileset (see `visualizer/README.md`) — note: superseded for now by the committed Circuit asset set; revisit if a richer look is wanted later
- [ ] Eval harness: scripted scenarios scoring agent output quality
- [ ] History windowing for long-running threads
- [ ] Approval hook reference implementation beyond CLI (Discord reaction or similar)

**Definition of done:** Event schema versioned, eval harness scores at least one scenario end to end, at least one non-CLI approval hook shipped as reference.

---

## Phase status

| Phase | Status | Date done |
|---|---|---|
| 0 — Extract the core | ✅ | 2025 |
| 1 — Tool library | ✅ | 2025 |
| 2 — CI and release hygiene | ✅ | 2025 |
| 3 — Observability + digest | ✅ | 2026-07-25 |
| 4 — Live spatial visualizer | ✅ | 2026-07-25 |
| 5 — Visualizer skin + bubble timing | ✅ | 2026-07-25 |
| 6 — HITL approval + local backend | ✅ | 2026-07-25 |
| 7 — Lock it in | ⬜ | |
